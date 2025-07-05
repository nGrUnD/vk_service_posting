
from src.celery_app import app

from src.services.auth import AuthService
from src.services.vk_token_service import TokenService
from src.utils.celery_error_handler import mark_vk_account_failure_by_task_id
from src.vk_api.vk_account import get_vk_account_data
from asgiref.sync import async_to_sync

def parse_vk_profile(vk_token, vk_account_id_database: int, proxy: str) -> dict:
    if not vk_token:
        raise ValueError("Не удалось получить токен.")

    vk_account_data = get_vk_account_data(vk_token, proxy)
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
        "token": vk_token,
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
