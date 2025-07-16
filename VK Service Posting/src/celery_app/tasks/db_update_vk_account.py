from src.celery_app import app
from src.celery_app.celery_db import SyncSessionLocal
from sqlalchemy import select
from src.models.vk_account_cred import VKAccountCredOrm
from src.models.vk_account import VKAccountOrm
from src.schemas.vk_account import VKAccountUpdate


def _update_vk_account_db(account_id_database: int, account_update_data: dict, groups_count: int):
    # assume get_one_or_none is async
    with SyncSessionLocal() as session:

        stmt = select(VKAccountOrm).where(VKAccountOrm.id == account_id_database)
        result = session.execute(stmt)
        account = result.scalars().one_or_none()

        if not account:
            raise ValueError(f"Account {account_id_database} not found")

        account_update_data = VKAccountUpdate(**account_update_data)
        # account_update_data.groups_count = len(groups)
        account_update_data.groups_count = groups_count

        account_update_data.parse_status = "success"

        # Применим обновление
        for field, value in account_update_data.model_dump(exclude_unset=True).items():
            setattr(account, field, value)

        session.commit()

@app.task
def update_db_sync(data: dict, account_id_database: int)->dict:
    groups_count = len(data["groups_data"]["groups"])
    _update_vk_account_db(account_id_database, data["vk_account_data"]["vk_account_data"], groups_count)
    return data