from src.celery_app import app
from src.celery_app.tasks.db_update_vk_account import _update_vk_account_db
from src.vk_api.vk_account import get_vk_session_by_log_pass


@app.task(bind=True)
def get_vk_account_cred(self, account_id_database: int, login: str, password: str, proxy: str) -> dict:
    try:
        vk_session = get_vk_session_by_log_pass(login, password, proxy)

        data = {
            "vk_session": vk_session,
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