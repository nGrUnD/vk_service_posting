import logging
import re

from src.celery_app import app
from src.celery_app.celery_db import SyncSessionLocal

from sqlalchemy import select

from src.models.vk_account import VKAccountOrm
from src.vk_api_methods.selenium.vk_selenium_captcha import vk_login
from src.celery_app.tasks.vk_account_backup_parse import parse_vk_profile_backup

@app.task(name="vk_checker_add_account")
def vk_checker_add_account(user_id, vk_account_id_db, login: str, password: str, proxy_http: str):
    database_manager = SyncSessionLocal()

    # Start Database Update
    update_db_vk_account_start(database_manager, vk_account_id_db)
    try:
        curl, vk_group_sub = vk_login(login, password, None, proxy_http)

        update_db_vk_account_end(database_manager, vk_account_id_db, curl, vk_group_sub)
        parse_vk_profile_backup(vk_account_id_db, proxy_http, user_id, "checker")
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

def update_db_vk_account_error(database_manager, vk_account_id: int, error: str):
    with database_manager as session:
        stmt = select(VKAccountOrm).where(VKAccountOrm.id == vk_account_id)
        result = session.execute(stmt)
        vk_account_db = result.scalars().one_or_none()

        if not vk_account_db:
            raise ValueError(f"VK Account {vk_account_id} not found in database")

        vk_account_db.name = "Maybe Blocked?\n" + error
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
            vk_account_db.account_type = "checker"

        session.commit()