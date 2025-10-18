import re
from typing import Optional

from src.celery_app import app
from src.celery_app.celery_db import SyncSessionLocal

from sqlalchemy import select

from src.celery_app.tasks import create_workpost
from src.models import VKGroupOrm
from src.models.vk_account import VKAccountOrm

from src.vk_api_methods.selenium.vk_selenium_captcha import vk_login
from src.celery_app.tasks.vk_account_backup_parse import parse_vk_profile_backup
from src.vk_api_methods.vk_account import get_vk_group_info
from src.vk_api_methods.vk_auth import get_new_token_request


@app.task(name="vk_account_autocurl")
def connect_vk_account_autocurl(user_id: int, vk_account_id: int, login: str, password: str, vk_group_url: str,
                                category_id_db: int,
                                proxy_http: str):
    database_manager = SyncSessionLocal()

    # Start Database Update
    update_db_vk_account_start(database_manager, vk_account_id)

    try:
        curl, vk_group_sub = vk_login(login, password, vk_group_url, proxy_http)
        update_db_vk_account_end(database_manager, vk_account_id, curl, vk_group_sub)
    except Exception as e:
        update_db_vk_account_error(database_manager, vk_account_id, str(e))
        raise e

    # End Database Update (Curl, token + cookie)
    parse_vk_profile_backup(vk_account_id, proxy_http, user_id)
    try_add_vk_group_main(database_manager, vk_account_id, vk_group_url, proxy_http, user_id)
    try_add_workerpost(database_manager, vk_account_id, vk_group_url, proxy_http, user_id, category_id_db)
    print(f"Account {vk_account_id}: Workerpost добавлен!")
    # update_db_vk_account_parse_task(database_manager, vk_account_id, task_parse.id)


def update_db_vk_account_start(database_manager, vk_account_id: int):
    with database_manager as session:
        stmt = select(VKAccountOrm).where(VKAccountOrm.id == vk_account_id)
        result = session.execute(stmt)
        vk_account_db = result.scalars().one_or_none()

        if not vk_account_db:
            raise ValueError(f"VK Account {vk_account_id} not found in database")

        vk_account_db.name = "started"
        session.commit()


def update_db_vk_account_error(database_manager, vk_account_id: int, error: str):
    with database_manager as session:
        stmt = select(VKAccountOrm).where(VKAccountOrm.id == vk_account_id)
        result = session.execute(stmt)
        vk_account_db = result.scalars().one_or_none()

        if not vk_account_db:
            raise ValueError(f"VK Account {vk_account_id} not found in database")

        vk_account_db.name = error
        session.commit()


def update_db_vk_account_end(database_manager, vk_account_id: int, curl: str, vk_group_sub: bool):
    print(f"curl: {curl}")
    print(f"vk_group_sub: {vk_group_sub}")
    with database_manager as session:
        stmt = select(VKAccountOrm).where(VKAccountOrm.id == vk_account_id)
        result = session.execute(stmt)
        vk_account_db = result.scalars().one_or_none()

        if not vk_account_db:
            raise ValueError(f"VK Account {vk_account_id} not found in database")

        if vk_group_sub:
            vk_account_db.name = "VK sub"
        else:
            vk_account_db.name = "No VK sub"

        if curl is None:
            vk_account_db.second_name = "No CURL"
        else:
            # =============
            access_token = re.search(r"access_token=([^&]+)", curl).group(1).split("'")[0]
            cookie = re.search(
                r"-b([^&]+)", curl).group(1).split("'")[1]

            vk_account_db.cookies = cookie
            vk_account_db.token = access_token

        session.commit()


def update_db_vk_account_parse_task(database_manager, vk_account_id: int, task_id: int):
    with database_manager as session:
        stmt = select(VKAccountOrm).where(VKAccountOrm.id == vk_account_id)
        result = session.execute(stmt)
        vk_account_db = result.scalars().one_or_none()

        if not vk_account_db:
            raise ValueError(f"VK Account {vk_account_id} not found in database")

        vk_account_db.task_id = task_id
        session.commit()


def try_add_vk_group_main(database_manager, vk_account_id: int, vk_group_url: str, proxy_http: str, user_id: int):
    vk_group_id = extract_vk_group_id(vk_group_url)

    with database_manager as session:
        stmt = select(VKGroupOrm).where(VKGroupOrm.vk_group_id == vk_group_id)
        result = session.execute(stmt)
        vk_group_db = result.scalars().one_or_none()

        if vk_group_db:
            return

        stmt = select(VKAccountOrm).where(VKAccountOrm.id == vk_account_id)
        result = session.execute(stmt)
        vk_account_db = result.scalars().one_or_none()

        stmt = select(VKAccountOrm).where(VKAccountOrm.account_type == "main")
        result = session.execute(stmt)
        vk_account_main_db = result.scalars().one_or_none()

        access_token = vk_account_db.access_token
        cookies = vk_account_db.cookies

        vk_token = get_new_token_request(access_token, cookies, proxy_http)
        vk_group_info = get_vk_group_info(vk_token, vk_group_id, proxy_http)

        group_new = VKGroupOrm(
            user_id=user_id,
            vk_group_id=vk_group_id,
            vk_admin_main_id=vk_account_main_db.id,
            vk_group_type="main",
            vk_group_url=vk_group_url,
            avatar_url=vk_group_info['avatar_url'],
            name=vk_group_info['name'],
            clips_count=1,
            parse_status="success",
            task_id=""
        )

        session.add(group_new)
        session.commit()

def try_add_workerpost(database_manager, vk_account_id: int, vk_group_url: str, proxy_http: str, user_id: int, category_id: int):
    vk_group_id = extract_vk_group_id(vk_group_url)
    with database_manager as session:
        stmt = select(VKAccountOrm).where(VKAccountOrm.id == vk_account_id)
        result = session.execute(stmt)
        vk_account_db = result.scalars().one_or_none()

        stmt = select(VKGroupOrm).where(VKGroupOrm.vk_group_id == vk_group_id)
        result = session.execute(stmt)
        vk_group_db = result.scalars().one_or_none()

        stmt = select(VKAccountOrm).where(VKAccountOrm.account_type == "main")
        result = session.execute(stmt)
        vk_account_main_db = result.scalars().one_or_none()


        access_token = vk_account_db.access_token
        cookies = vk_account_db.cookies

        try:
            vk_token = get_new_token_request(access_token, cookies, proxy_http)
            create_workpost(
                user_id,
                vk_account_id,
                vk_account_main_db.id,
                vk_group_db.id,
                category_id,
                vk_token,
                database_manager,
                proxy_http
            )
        except Exception as e:
            print(e)
            raise e

def extract_vk_group_id(vk_group_url: str) -> Optional[str]:
    """
    Извлекает ID группы из URL VK.

    Поддерживаемые форматы:
    - https://vk.com/club227197531 -> 227197531
    - https://vk.com/public123456 -> 123456
    - vk.com/club123 -> 123
    - https://vk.ru/public999 -> 999
    - https://vk.com/mygroup -> mygroup (короткое имя)
    - https://vk.com/id123456 -> id123456

    :param vk_group_url: URL группы VK
    :return: ID группы (число или короткое имя) или None
    """
    if not vk_group_url:
        return None

    # Убираем пробелы
    url = vk_group_url.strip()

    # Паттерн для извлечения ID
    # Ищем club123, public123, или любой другой идентификатор после vk.com/ или vk.ru/
    pattern = r'(?:https?://)?(?:www\.)?vk\.(?:com|ru)/(?:club|public)?(\d+|[a-zA-Z0-9_]+)'

    match = re.search(pattern, url)
    if match:
        group_id = match.group(1)
        return group_id

    return None