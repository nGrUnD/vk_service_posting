
from src.celery_app import app

from src.services.auth import AuthService
from src.services.vk_token_service import TokenService
from src.utils.celery_error_handler import mark_vk_account_failure_by_task_id
from src.vk_api.vk_account import get_vk_account_data
from asgiref.sync import async_to_sync

async def parse_vk_profile(curl_encrypted: str, vk_account_id_database: int) -> dict:
    curl = AuthService().decrypt_data(curl_encrypted)

    token = TokenService.get_token_from_curl(curl)
    if not token:
        raise ValueError("Не удалось получить токен.")

    vk_account_data = get_vk_account_data(token)
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
    }

    return data


@app.task(bind=True)
def parse_vk_profile_sync(self, data: dict):
    curl_enc = data["encrypted_curl"]
    vk_account_id_database = data["vk_account_id_database"]  # Если добавишь в return
    try:
        result = async_to_sync(parse_vk_profile)(curl_enc, vk_account_id_database)
        return result
    except Exception as e:
        async_to_sync(mark_vk_account_failure_by_task_id)(vk_account_id_database)
        raise
