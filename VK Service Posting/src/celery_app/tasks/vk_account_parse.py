from sqlalchemy import select

from src.celery_app import app
from src.celery_app.celery_db import SyncSessionLocal
from src.models.vk_account import VKAccountOrm
from src.models.vk_account_cred import VKAccountCredOrm
from src.services.auth import AuthService

from src.utils.celery_error_handler import mark_vk_account_failure_by_task_id
from src.vk_api.vk_account import get_vk_account_data, get_vk_session_by_token, get_vk_session_by_log_pass


def get_vk_account_data_retry(vk_account_id_db: int, proxy: str, retries: int = 10):

    last_proxy = proxy
    with SyncSessionLocal() as session:
        stmt = select(VKAccountOrm).where(VKAccountOrm.id == vk_account_id_db)
        result = session.execute(stmt)
        vk_account_database = result.scalars().one_or_none()

        if vk_account_database is None:
            raise ValueError(f"VkAccount с id {vk_account_database} не найден в базе")


        stmt = select(VKAccountCredOrm).where(VKAccountCredOrm.id == vk_account_database.vk_cred_id)
        result = session.execute(stmt)
        vk_cred_database = result.scalars().one_or_none()

        if vk_cred_database is None:
            raise ValueError(f"VkAccountCred с id {vk_account_database.vk_cred_id} не найден в базе")

        login = vk_cred_database.login
        password = AuthService().decrypt_data(vk_cred_database.encrypted_password)

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
    if not vk_token:
        raise ValueError("Не удалось получить токен.")

    vk_session = get_vk_session_by_token(vk_token, proxy)
    token_data = vk_session.token
    token = token_data['access_token']

    try:
        vk_account_data = get_vk_account_data(token, proxy)
    except Exception as e:
        print(e)
        vk_account_data, token = get_vk_account_data_retry(vk_account_id_database, proxy)


    vk_account_id = vk_account_data["id"]
    #vk_groups_data = get_vk_account_admin_groups(token, vk_account_id)
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

    data = {
        "token": token,
        "vk_account_id": vk_account_id,
        "vk_account_id_database": vk_account_id_database,
        "vk_account_data": vk_account_data,
        "proxy": proxy,
    }

    return data


@app.task(bind=True)
def parse_vk_profile_sync(self, data: dict):
    vk_token = data["token"]
    vk_account_id_database = data["vk_account_id_database"]  # Если добавишь в return
    proxy = data["proxy"]
    try:
        result = parse_vk_profile(vk_token, vk_account_id_database, proxy)
        return result
    except Exception as e:
        mark_vk_account_failure_by_task_id(vk_account_id_database)
        raise
