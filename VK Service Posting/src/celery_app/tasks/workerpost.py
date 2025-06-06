from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.api.dependencies import get_database
from src.celery_app import app
from asgiref.sync import async_to_sync

from src.config import settings
from src.repositories.vk_account import VKAccountRepository
from src.repositories.vk_group import VKGroupRepository
from src.schemas.celery_task import CeleryTaskUpdate
from src.schemas.vk_account import VKAccountUpdate
from src.schemas.workerpost import WorkerPostAdd
from src.services.auth import AuthService
from src.services.vk_token_service import TokenService
from src.utils.database_manager import DataBaseManager
from src.vk_api.vk_account import get_vk_account_data
from src.vk_api.vk_group import join_group, assign_editor_role
from src.vk_api.vk_selenium import get_vk_account_curl_from_browser

async def _update_vk_account_db(account_id_database: int, account_update_data: dict, encrypted_curl: str):
    # assume get_one_or_none is async
    engine = create_async_engine(settings.DB_URL, future=True)
    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    database_manager = DataBaseManager(AsyncSessionLocal)
    async with database_manager as database:
        account = await database.vk_account.get_one_or_none(id=account_id_database)

        if not account:
            raise ValueError(f"Account {account_id_database} not found")

        account_update_data = VKAccountUpdate(**account_update_data)
        # account_update_data.groups_count = len(groups)
        account_update_data.groups_count = 1
        account_update_data.encrypted_curl=encrypted_curl

        account_update_data.parse_status = "success"

        await database.vk_account.edit(account_update_data, exclude_unset=True, id=account_id_database)

        await database.commit()


async def parse_vk_profile(curl_encrypted: str, vk_account_id_database: int) -> dict:
    curl = AuthService().decrypt_data(curl_encrypted)

    token = TokenService.get_token_from_curl(curl)
    if not token:
        raise ValueError("Не удалось получить токен.")

    vk_account_data = get_vk_account_data(token)
    vk_account_id = vk_account_data["id"]
    #vk_groups_data = get_vk_account_admin_groups(token, vk_account_id)
    vk_count_groups = 1
    vk_link = f"https://vk.com/id{vk_account_id}"

    vk_account_data = {
        "vk_account_id": vk_account_id,
        "name": vk_account_data["name"],
        "second_name": vk_account_data["second_name"],
        "vk_account_url": vk_link,
        "avatar_url": vk_account_data["avatar_url"],
        "groups_count": vk_count_groups,
    }

    data = {
        "token": token,
        "vk_account_id": vk_account_id,
        "vk_account_id_database": vk_account_id_database,
        "vk_account_data": vk_account_data,
    }
    return data

async def create_workpost(
        user_id: int,
        account_id_database: int,
        main_account_id_database: int,
        vk_group_id_database: int,
        category_id_database: int,
        account_token: str,
):

    engine = create_async_engine(settings.DB_URL, future=True)
    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    database_manager = DataBaseManager(AsyncSessionLocal)
    async with database_manager as database:
        vk_account_database = await database.vk_account.get_one_or_none(id=account_id_database)
        vk_main_account_database = await database.vk_account.get_one_or_none(id=main_account_id_database)
        vk_group_database = await database.vk_group.get_one_or_none(id=vk_group_id_database)
        category_database = await database.category.get_one_or_none(id=category_id_database)

        join_group(vk_group_database.vk_group_id, account_token)

        main_account_curl = AuthService().decrypt_data(vk_main_account_database.encrypted_curl)
        main_account_token = TokenService.get_token_from_curl(main_account_curl)

        assign_editor_role(vk_group_database.vk_group_id, vk_account_database.vk_account_id, main_account_token)

        workerpost_add = WorkerPostAdd(
            user_id=user_id,
            vk_group_id=vk_group_database.id,
            vk_account_id=vk_account_database.id,
            category_id=category_database.id,
            is_active=category_database.is_active,
            last_post_at=None,
        )

        await database.workerpost.add(workerpost_add)
        await database.commit()

async def update_celery_task_status(
    account_id_database: int,
    new_status: str,
):
    engine = create_async_engine(settings.DB_URL, future=True)
    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    database_manager = DataBaseManager(AsyncSessionLocal)
    async with database_manager as database:
        celery_task = await database.celery_task.get_one_or_none(vk_account_id=account_id_database)

        celery_task_update = CeleryTaskUpdate(
            status=new_status
        )
        await database.celery_task.edit(celery_task_update, exclude_unset=True, id=celery_task.id)
        await database.commit()

@app.task
def create_workpost_account(
        account_id_database: int,
        main_account_id_database: int,
        vk_group_id_database: int,
        category_id_database: int,
        user_id: int,
        login: str,
        password: str,
):
    print("Задача началась!")
    try:
        curl = async_to_sync(get_vk_account_curl_from_browser)(login, password)
        encrypted_curl = AuthService().encrypt_data(curl)

        vk_account_parse_data = async_to_sync(parse_vk_profile)(encrypted_curl, account_id_database)
        # token
        # vk_account_id
        # vk_account_id_database
        # vk_account_data
        async_to_sync(_update_vk_account_db)(account_id_database, vk_account_parse_data['vk_account_data'], encrypted_curl)

        async_to_sync(create_workpost)(
            user_id,
            account_id_database,
            main_account_id_database,
            vk_group_id_database,
            category_id_database,
            vk_account_parse_data['token'],
        )

        async_to_sync(update_celery_task_status)(account_id_database, "success")


    except Exception as e:
        async_to_sync(update_celery_task_status)(account_id_database, "failed")
        raise