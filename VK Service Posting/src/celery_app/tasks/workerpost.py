import random

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
from src.utils.database_manager import DataBaseManager
from src.vk_api.vk_account import get_vk_account_data, get_vk_session_by_log_pass
from src.vk_api.vk_group import join_group, assign_editor_role
from src.vk_api.vk_selenium import get_vk_account_curl_from_browser
from src.celery_app.celery_db import SyncSessionLocal
import vk_api

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


def parse_vk_profile(vk_token: str, vk_account_id_database: int, proxy: str = None) -> dict:

    if not vk_token:
        raise ValueError("Не удалось получить токен.")

    vk_account_data = get_vk_account_data(vk_token, proxy)
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
        "token": vk_token,
        "vk_account_id": vk_account_id,
        "vk_account_id_database": vk_account_id_database,
        "vk_account_data": vk_account_data,
    }
    return data

def create_workpost(
        user_id: int,
        account_id_database: int,
        main_account_id_database: int,
        vk_group_id_database: int,
        category_id_database: int,
        account_token: str,
        database_manager,
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

        join_group(vk_group_database.vk_group_id, account_token)

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
        stmt = select(CeleryTaskOrm).where(CeleryTaskOrm.vk_account_id == account_id_database)
        result = session.execute(stmt)
        celery_task = result.scalars().one_or_none()

        celery_task.status = new_status
        session.commit()

def get_vk_session_with_retry(database_manager, account_id_database: int, login: str, password: str, proxy: str = None, retries: int = 10):
    last_proxy = proxy
    with database_manager as session:
        stmt = select(VKAccountOrm).where(VKAccountOrm.id == account_id_database)
        result = session.execute(stmt)
        vk_account_database = result.scalars().one_or_none()
        if vk_account_database is None:
            raise ValueError(f"VkAccount с логином {login} не найден в базе")

        for attempt in range(1, retries + 1):
            try:
                vk_session = get_vk_session_by_log_pass(login=login, password=password, proxy=last_proxy)

                if last_proxy and last_proxy != vk_account_database.proxy_string:
                    # Находим объект Proxy в базе
                    stmt_proxy = select(ProxyOrm).where(ProxyOrm.http == last_proxy)
                    proxy_db = session.execute(stmt_proxy).scalars().one_or_none()
                    if proxy_db:
                        vk_account_database.proxy_id = proxy_db.id
                        session.commit()

                return vk_session
            except Exception as e:
                print(f"Попытка {attempt}: ошибка авторизации, пробуем другой прокси")
                stmt_proxies = select(ProxyOrm).where(ProxyOrm.http != last_proxy)
                proxies = session.execute(stmt_proxies).scalars().all()

                if not proxies:
                    print("Нет доступных прокси для смены. Повторяем попытку с текущим прокси.")
                    continue

                last_proxy = random.choice(proxies).proxy_string

    raise ValueError(f"Не удалось авторизоваться после {retries} попыток")

@app.task
def create_workpost_account(
        account_id_database: int,
        main_account_id_database: int,
        vk_group_id_database: int,
        category_id_database: int,
        user_id: int,
        login: str,
        password: str,
        proxy: str,
):
    print("Задача началась!")
    database_manager = SyncSessionLocal()
    try:
        vk_session = get_vk_session_with_retry(
            database_manager=database_manager,
            account_id_database=account_id_database,
            login=login,
            password=password,
            proxy=proxy,
        )
        token_data = vk_session.token
        vk_token = token_data['access_token']
        #curl = get_vk_account_curl_from_browser(login, password, proxy)
        #encrypted_curl = AuthService().encrypt_data(curl)

        vk_account_parse_data = parse_vk_profile(vk_token, account_id_database, proxy)
        # token
        # vk_account_id
        # vk_account_id_database
        # vk_account_data
        _update_vk_account_db(account_id_database, vk_account_parse_data['vk_account_data'], vk_token, database_manager)

        create_workpost(
            user_id,
            account_id_database,
            main_account_id_database,
            vk_group_id_database,
            category_id_database,
            vk_account_parse_data['token'],
            database_manager
        )

        update_celery_task_status(account_id_database, "success", database_manager)


    except Exception as e:
        update_celery_task_status(account_id_database, "failed", database_manager)
        raise