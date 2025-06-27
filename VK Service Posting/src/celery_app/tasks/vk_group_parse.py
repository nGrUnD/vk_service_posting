
from src.celery_app import app
from src.vk_api.vk_account import get_vk_account_admin_groups
from asgiref.sync import async_to_sync

async def parse_vk_group(token: str, vk_account_id: int) -> dict:

    vk_groups_data = get_vk_account_admin_groups(token, vk_account_id)
    return vk_groups_data


@app.task(bind=True)
def parse_vk_group_sync(self, data: dict):
    try:
        result = async_to_sync(parse_vk_group)(
            data["token"],
            data["vk_account_id"]
        )
        return {
            "groups_data": result,
            "vk_account_data": data,
        }
    except Exception as e:
        raise