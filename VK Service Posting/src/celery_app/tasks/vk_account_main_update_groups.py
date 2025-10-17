from src.celery_app import app
from src.celery_app.celery_db import SyncSessionLocal
from src.celery_app.tasks.vk_account_parse import get_vk_account_admin_groups
from src.celery_app.tasks.vk_account_parse import update_db_vk_account
from src.celery_app.tasks.vk_account_parse import update_vk_groups_database
from src.celery_app.tasks.vk_account_parse import parse_vk_profile
from src.vk_api_methods.vk_auth import get_new_token_request


@app.task(name="vk_account_main_update_groups")
def vk_account_main_update_groups(user_id: int, vk_account_id_db: int, vk_account_id: int, cookie: str, access_token: str, proxy_http: str):
    database_manager = SyncSessionLocal()
    vk_token = get_new_token_request(access_token, cookie, proxy_http)

    groups_data = get_vk_account_admin_groups(vk_token, vk_account_id, proxy_http)

    groups_groups_data = groups_data["groups"]
    groups_count = len(groups_groups_data)

    vk_account_data = parse_vk_profile(vk_token, vk_account_id_db, proxy_http)

    update_db_vk_account(database_manager, vk_account_id_db, vk_account_data, groups_count)
    update_vk_groups_database(database_manager, vk_account_id_db, user_id, groups_groups_data)