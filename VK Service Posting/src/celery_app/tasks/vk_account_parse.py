from sqlalchemy import select

from src.celery_app import app
from src.celery_app.celery_db import SyncSessionLocal
from src.models.vk_account import VKAccountOrm
from src.models.vk_group import VKGroupOrm
from src.services.auth import AuthService

from src.vk_api_methods.vk_account import get_vk_account_data, get_vk_session_by_token, get_vk_session_by_log_pass, \
    get_vk_account_admin_groups


def get_vk_account_data_retry(vk_account_id_db: int, proxy: str, retries: int = 10):
    last_proxy = proxy
    with SyncSessionLocal() as session:
        stmt = select(VKAccountOrm).where(VKAccountOrm.id == vk_account_id_db)
        result = session.execute(stmt)
        vk_account_database = result.scalars().one_or_none()

        if vk_account_database is None:
            raise ValueError(f"VkAccount с id {vk_account_database} не найден в базе")


        login = vk_account_database.login
        password = AuthService().decrypt_data(vk_account_database.encrypted_password)

        for attempt in range(1, retries + 1):
            try:
                vk_session = get_vk_session_by_log_pass(login=login, password=password, proxy=last_proxy)
                token_data = vk_session.token
                token = token_data['access_token']
                vk_account_data = get_vk_account_data(token, proxy)


                return vk_account_data, token
            except Exception as e:
                print(e)
                print(f"Попытка {attempt}: ошибка авторизации")

    raise ValueError(f"Не удалось авторизоваться после {retries} попыток")


def parse_vk_profile(vk_token, vk_account_id_database: int, proxy: str) -> dict:
    try:
        vk_account_data = get_vk_account_data(vk_token, proxy)
    except Exception as e:
        print(e)
        vk_account_data, token = get_vk_account_data_retry(vk_account_id_database, proxy)


    vk_account_id = vk_account_data["id"]
    vk_count_groups = 0
    vk_link = f"https://vk.com/id{vk_account_id}"

    vk_account_data = {
        "vk_account_id": vk_account_id,
        "name": vk_account_data["name"],
        "second_name": vk_account_data["second_name"],
        "vk_account_url": vk_link,
        "avatar_url": vk_account_data["avatar_url"],
        "groups_count": vk_count_groups,
    }

    return vk_account_data

def update_db_vk_account(database_manager, vk_account_id_database: int, data: dict, count_groups: int):
    with database_manager as session:
        stmt = select(VKAccountOrm).where(VKAccountOrm.id == vk_account_id_database)
        result = session.execute(stmt)
        account = result.scalars().one_or_none()

        if not account:
            raise ValueError(f"Account {vk_account_id_database} not found")

        account.vk_account_id = data['vk_account_id']
        account.name = data['name']
        account.second_name = data['second_name']
        account.vk_account_url = data['vk_account_url']
        account.avatar_url = data['avatar_url']
        account.groups_count = count_groups
        account.parse_status = "success"

        session.commit()

def _add_or_edit_vk_group_db(session, data: dict, vk_account_id_database: int, user_id: int):
    print(f"group data: {data}")
    vk_group_id = data["group_id"]
    vk_group_url = data["vk_group_url"]
    avatar_url = data["avatar_url"]
    name = data["name"]
    clips_count = data["clips_count"]

    stmt = select(VKGroupOrm).where(VKGroupOrm.vk_group_id == vk_group_id)
    result = session.execute(stmt)
    group = result.scalars().one_or_none()

    if not group:
        group_new = VKGroupOrm(
            user_id=user_id,
            vk_group_id=vk_group_id,
            vk_admin_main_id=vk_account_id_database,
            vk_group_type="main",
            vk_group_url=vk_group_url,
            avatar_url=avatar_url,
            name=name,
            clips_count=clips_count,
            parse_status="success",
            task_id=""
        )

        session.add(group_new)
        return

    group.user_id = user_id
    group.vk_admin_main_id = vk_account_id_database
    group.vk_group_url = vk_group_url
    group.avatar_url = avatar_url
    group.name = name
    group.clips_count = clips_count
    group.vk_group_type = "main"
    group.parse_status = "success"


def update_vk_groups_database(database_manager, vk_account_id_database: int, user_id: int, groups_data: dict):
    with database_manager as session:
        for group_data in groups_data:
            _add_or_edit_vk_group_db(session, group_data, vk_account_id_database, user_id)
        session.commit()

def mark_vk_account_failure_by_task_id(database_manager, vk_account_id: int):
    with database_manager as session:
        stmt = select(VKAccountOrm).where(VKAccountOrm.id == vk_account_id)
        result = session.execute(stmt)
        account = result.scalars().one_or_none()
        if not account:
            return

        account.parse_status = "failure"
        print(f"vk_account: {vk_account_id}")
        session.commit()

@app.task
def parse_vk_profile_main_sync(vk_token: str, vk_account_id_database: int, proxy: str, user_id: int):
    database_manager = SyncSessionLocal()
    try:
        vk_account_data = parse_vk_profile(vk_token, vk_account_id_database, proxy)
        groups_data = get_vk_account_admin_groups(vk_token, vk_account_id_database, proxy)

        groups_count = len(groups_data["groups_data"]["groups"])

        update_db_vk_account(database_manager, vk_account_id_database, vk_account_data, groups_count)
        update_vk_groups_database(database_manager, vk_account_id_database, user_id, groups_data)

    except Exception as e:
        mark_vk_account_failure_by_task_id(database_manager, vk_account_id_database)
        raise
