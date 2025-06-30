from sqlalchemy import select

from src.celery_app import app
from src.models.vk_group import VKGroupOrm
from src.celery_app.celery_db import SyncSessionLocal


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

def _update_vk_account_group_db(groups_data: dict, vk_account_id_database: int, user_id: int):
    with SyncSessionLocal() as session:
        for group_data in groups_data:
            _add_or_edit_vk_group_db(session, group_data, vk_account_id_database, user_id)
        session.commit()


@app.task
def update_db_group_async(data: dict, vk_account_id_database: int, user_id: int):
    _update_vk_account_group_db(data["groups_data"]["groups"], vk_account_id_database, user_id)
    return data
