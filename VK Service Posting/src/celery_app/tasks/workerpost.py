import random
import time

from sqlalchemy import select

from src.celery_app import app
from src.models.category import CategoryOrm
from src.models.celery_task import CeleryTaskOrm
from src.models.proxy import ProxyOrm
from src.models.vk_account import VKAccountOrm
from src.models.vk_group import VKGroupOrm
from src.models.workerpost import WorkerPostOrm
from src.schemas.vk_account import VKAccountUpdate
from src.services.auth import AuthService
from src.services.vk_token_service import TokenService
from src.utils.cookiejar import list_to_cookiejar
from src.vk_api_methods.vk_account import get_vk_account_data
from src.vk_api_methods.vk_auth import get_token, get_new_token
from src.vk_api_methods.vk_group import join_group, assign_editor_role
from src.celery_app.celery_db import SyncSessionLocal

def _update_vk_account_db(account_id_database: int, account_update_data: dict, vk_token: str, database_manager,):
    # assume get_one_or_none is async
    with database_manager as session:
        stmt = select(VKAccountOrm).where(VKAccountOrm.id == account_id_database)
        result = session.execute(stmt)
        account = result.scalars().one_or_none()

        if not account:
            raise ValueError(f"Account {account_id_database} not found")

        account_update_data = VKAccountUpdate(**account_update_data)
        # account_update_data.groups_count = len(groups)
        account_update_data.groups_count = 1
        account_update_data.encrypted_curl=""

        account_update_data.parse_status = "success"

        for field, value in account_update_data.model_dump(exclude_unset=True).items():
            setattr(account, field, value)

        session.commit()

def create_workpost(
        user_id: int,
        account_id_database: int,
        main_account_id_database: int,
        vk_group_id_database: int,
        category_id_database: int,
        account_token: str,
        database_manager,
        proxy: str,
):
    with database_manager as session:
        stmt = select(VKAccountOrm).where(VKAccountOrm.id == account_id_database)
        result = session.execute(stmt)
        vk_account_database = result.scalars().one_or_none()

        stmt = select(VKAccountOrm).where(VKAccountOrm.id == main_account_id_database)
        result = session.execute(stmt)
        vk_main_account_database = result.scalars().one_or_none()

        stmt = select(VKGroupOrm).where(VKGroupOrm.id == vk_group_id_database)
        result = session.execute(stmt)
        vk_group_database = result.scalars().one_or_none()

        stmt = select(CategoryOrm).where(CategoryOrm.id == category_id_database)
        result = session.execute(stmt)
        category_database = result.scalars().one_or_none()

        join_group(vk_group_database.vk_group_id, account_token, proxy)

        main_account_curl = AuthService().decrypt_data(vk_main_account_database.encrypted_curl)
        main_account_token = TokenService.get_token_from_curl(main_account_curl)

        assign_editor_role(vk_group_database.vk_group_id, vk_account_database.vk_account_id, main_account_token)

        workerpost_add = WorkerPostOrm(
            user_id=user_id,
            vk_group_id=vk_group_database.id,
            vk_account_id=vk_account_database.id,
            category_id=category_database.id,
            is_active=category_database.is_active,
            last_post_at=None,
        )

        session.add(workerpost_add)
        session.commit()

def update_celery_task_status(
    account_id_database: int,
    new_status: str,
    database_manager,
):
    with database_manager as session:
        stmt = select(CeleryTaskOrm).where(CeleryTaskOrm.vk_account_id == account_id_database, CeleryTaskOrm.type=="add workerpost")
        result = session.execute(stmt)
        celery_task = result.scalars().one_or_none()

        celery_task.status = new_status
        session.commit()

@app.task
def create_workpost_account(
        account_id_database: int,
        main_account_id_database: int,
        vk_group_id_database: int,
        category_id_database: int,
        user_id: int,
        login: str,
        password: str,
        token_db : str,
        cookie_db,
        proxy: str,
):
    print("Задача началась!")
    database_manager = SyncSessionLocal()
    try:

        cookie = list_to_cookiejar(cookie_db)
        vk_token = get_new_token(token_db, cookie, proxy)
        #vk_token = get_token(login=login, password=password, proxy_http=proxy)
        #curl = get_vk_account_curl_from_browser(login, password, proxy)
        #encrypted_curl = AuthService().encrypt_data(curl)

        #vk_account_parse_data = parse_vk_profile(vk_token, account_id_database, proxy)
        # token
        # vk_account_id
        # vk_account_id_database
        # vk_account_data
        #_update_vk_account_db(account_id_database, vk_account_parse_data['vk_account_data'], vk_token, database_manager)

        create_workpost(
            user_id,
            account_id_database,
            main_account_id_database,
            vk_group_id_database,
            category_id_database,
            vk_token,
            database_manager,
            proxy
        )

        update_celery_task_status(account_id_database, "success", database_manager)


    except Exception as e:
        update_celery_task_status(account_id_database, "failed", database_manager)
        raise