import re

from src.celery_app import app
from src.celery_app.celery_db import SyncSessionLocal

from sqlalchemy import select
from src.models.vk_account import VKAccountOrm

from src.vk_api_methods.selenium.vk_selenium_captcha import vk_login
from src.celery_app.tasks.vk_account_backup_parse import parse_vk_profile_backup_sync


@app.task(name="vk_account_autocurl")
def connect_vk_account_autocurl(user_id: int, vk_account_id: int, login: str, password: str, vk_group_url: str,
                                proxy_http: str):
    database_manager = SyncSessionLocal()

    # Start Database Update
    update_db_vk_account_start(database_manager, vk_account_id)

    try:
        curl, vk_group_sub = vk_login(login, password, vk_group_url, proxy_http)
    except Exception as e:
        update_db_vk_account_error(database_manager, vk_account_id, str(e))
        raise e

    # End Database Update (Curl, token + cookie)
    update_db_vk_account_end(database_manager, vk_account_id, curl, vk_group_sub)

    # New Task Parse VK Account + Database Update task id
    task_parse = parse_vk_profile_backup_sync.delay(vk_account_id, proxy_http, user_id)
    update_db_vk_account_parse_task(database_manager, vk_account_id, task_parse.id)


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