from asgiref.sync import async_to_sync
from src.celery_app import app
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.config import settings

from src.repositories.vk_account import VKAccountRepository
from src.repositories.vk_group import VKGroupRepository
from src.schemas.vk_account import VKAccountUpdate


async def _update_vk_account_db(account_id_database: int, account_update_data: dict, groups_count: int):
    # assume get_one_or_none is async
    engine = create_async_engine(settings.DB_URL, future=True)
    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        repo = VKAccountRepository(session)
        group_repo = VKGroupRepository(session)

        account = await repo.get_one_or_none(id=account_id_database)
        #groups = await group_repo.get_all_filtered(vk_admin_main_id=account_id_database)

        if not account:
            raise ValueError(f"Account {account_id_database} not found")

        account_update_data = VKAccountUpdate(**account_update_data)
        #account_update_data.groups_count = len(groups)
        account_update_data.groups_count = groups_count

        account_update_data.parse_status = "success"


        await repo.edit(account_update_data, exclude_unset=True, id=account_id_database)

        await session.commit()

@app.task
def update_db_sync(data: dict, account_id_database: int)->dict:
    groups_count = len(data["groups_data"]["groups"])
    async_to_sync(_update_vk_account_db)(account_id_database, data["vk_account_data"]["vk_account_data"], groups_count)
    return data