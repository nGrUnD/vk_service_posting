
from src.celery_app import app
from src.vk_api_methods.vk_account import get_vk_account_admin_groups

def parse_vk_group(token: str, vk_account_id: int, proxy: str) -> dict:
    vk_groups_data = get_vk_account_admin_groups(token, vk_account_id, proxy)
    return vk_groups_data


@app.task(bind=True)
def parse_vk_group_sync(self, data: dict):
    try:
        result = parse_vk_group(
            data["token"],
            data["vk_account_id"],
            data["proxy"],
        )
        return {
            "groups_data": result,
            "vk_account_data": data,
        }
    except Exception as e:
        raise e