from src.celery_app import app
from src.celery_app.tasks.db_update_vk_account import _update_vk_account_db
from src.vk_api_methods.vk_selenium import get_vk_account_curl_from_browser
from src.services.auth import AuthService


@app.task(bind=True)
def get_vk_account_curl(self, account_id_database: int, login: str, password: str, proxy: str) -> dict:
    try:
        curl = get_vk_account_curl_from_browser(login, password, proxy)
        encrypted_curl = AuthService().encrypt_data(curl)

        data = {
            "encrypted_curl": encrypted_curl,
            "vk_account_id_database": account_id_database,
            "proxy": proxy,
        }

        _update_vk_account_db(account_id_database=account_id_database, account_update_data=data, groups_count=0)

        return data

    except Exception as exc:
        # При ошибке обновляем статус и имя
        error_data = {
            "parse_status": "failed",
            "name": "failed flood_control",
            "second_name": "failed flood_control",
            "flood_control": True,
        }
        _update_vk_account_db(account_id_database=account_id_database, account_update_data=error_data, groups_count=0)

        # Можно логировать ошибку, например:
        #self.retry(exc=exc, countdown=60, max_retries=3)  # если хотите повторять задачу
        # Или просто вернуть ошибку без повторов:
        raise

        # Если не нужно повторять, раскомментируйте raise и удалите self.retry
