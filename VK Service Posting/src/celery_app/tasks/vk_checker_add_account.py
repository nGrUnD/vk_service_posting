import logging
import re
from typing import Optional

from src.celery_app import app
from src.celery_app.celery_db import SyncSessionLocal
from src.services.vk_token_service import TokenService

from sqlalchemy import select

from src.models.vk_account import VKAccountOrm
from src.celery_app.tasks.vk_account_backup_parse import parse_vk_profile_backup
from src.celery_app.tasks.vk_selenium_login_retry import vk_login_with_proxy_retry

@app.task(name="vk_checker_add_account")
def vk_checker_add_account(user_id, vk_account_id_db, login: str, password: str, proxy_http: str):
    database_manager = SyncSessionLocal()

    # Start Database Update
    update_db_vk_account_start(database_manager, vk_account_id_db)
    try:
        curl, vk_group_sub, access_token, _used_proxy = vk_login_with_proxy_retry(
            database_manager,
            vk_account_id_db,
            login,
            password,
            None,
            proxy_http,
        )

        update_db_vk_account_end(database_manager, vk_account_id_db, curl, vk_group_sub, access_token)
        parse_vk_profile_backup(
            vk_account_id_db, _used_proxy or proxy_http, user_id, "checker"
        )
    except Exception as e:
        update_db_vk_account_error(database_manager, vk_account_id_db, str(e))
        raise e


def update_db_vk_account_start(database_manager, vk_account_id: int):
    with database_manager as session:
        stmt = select(VKAccountOrm).where(VKAccountOrm.id == vk_account_id)
        result = session.execute(stmt)
        vk_account_db = result.scalars().one_or_none()

        if not vk_account_db:
            raise ValueError(f"VK Account {vk_account_id} not found in database")

        vk_account_db.name = "started"
        session.commit()

def _display_error_prefix(message: str) -> str:
    m = (message or "").lower()
    if "proxy tunnel" in m or "err_tunnel" in m or "err_proxy" in m:
        return "Proxy / сеть\n"
    if "login form did not open" in m or "password form" in m or "timeout" in m:
        return "VK / Selenium (таймаут UI)\n"
    if "captcha" in m or "заблок" in m or "block" in m:
        return "Капча / блокировка?\n"
    return "Ошибка входа\n"


def update_db_vk_account_error(database_manager, vk_account_id: int, error: str):
    with database_manager as session:
        stmt = select(VKAccountOrm).where(VKAccountOrm.id == vk_account_id)
        result = session.execute(stmt)
        vk_account_db = result.scalars().one_or_none()

        if not vk_account_db:
            raise ValueError(f"VK Account {vk_account_id} not found in database")

        vk_account_db.name = _display_error_prefix(error) + error
        session.commit()

def extract_cookie_from_curl(curl: str) -> Optional[str]:
    token_request = TokenService.parse_curl(curl)
    if not token_request or not token_request.cookies:
        return None

    return "; ".join(f"{key}={value}" for key, value in token_request.cookies.items())


def extract_access_token_from_curl(curl: str) -> Optional[str]:
    match = re.search(r"access_token=([^&]+)", curl)
    if not match:
        return None

    return match.group(1).split("'")[0]


def update_db_vk_account_end(database_manager, vk_account_id: int, curl: str, vk_group_sub: bool,
                             access_token: Optional[str] = None):
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
            cookie = extract_cookie_from_curl(curl)
            access_token = access_token or extract_access_token_from_curl(curl)

            if not access_token:
                vk_account_db.second_name = "No access_token"
            elif not cookie:
                vk_account_db.second_name = "No cookies"
            else:
                vk_account_db.cookies = cookie
                vk_account_db.token = access_token
                vk_account_db.account_type = "checker"

        session.commit()