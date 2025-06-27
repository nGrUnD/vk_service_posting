from asgiref.sync import async_to_sync
from src.celery_app import app
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.config import settings

from src.repositories.vk_group import VKGroupRepository
from src.schemas.vk_group import VKGroupUpdate, VKGroupAdd
from src.celery_app.celery_db import AsyncSessionLocal

async def _add_or_edit_vk_group_db(session, data: dict, vk_account_id_database: int, user_id: int):
    repo = VKGroupRepository(session)

    print(f"group data: {data}")
    vk_group_id = data["group_id"]
    vk_group_url = data["vk_group_url"]
    avatar_url = data["avatar_url"]
    name = data["name"]
    clips_count = data["clips_count"]
    get_group = await repo.get_one_or_none(vk_group_id=vk_group_id)

    if not get_group:
        group_new = VKGroupAdd(
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
        group_new.parse_status = "success"
        group_new.vk_admin_main_id=vk_account_id_database

        await repo.add(group_new)
        await session.commit()

        return

    group_update = VKGroupUpdate(
        user_id=user_id,
        vk_group_id=vk_group_id,
        vk_admin_main_id=vk_account_id_database,
        vk_group_type="main",
        vk_group_url=vk_group_url,
        avatar_url=avatar_url,
        name=name,
        clips_count=clips_count,
        parse_status="success",
    )

    group_update.parse_status = "success"

    await repo.edit(group_update, exclude_unset=True, vk_group_id=vk_group_id)


async def _update_vk_account_group_db(groups_data: dict, vk_account_id_database: int, user_id: int):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            for group_data in groups_data:
                await _add_or_edit_vk_group_db(session, group_data, vk_account_id_database, user_id)
            await session.commit()

@app.task
async def update_db_group_async(data: dict, vk_account_id_database: int, user_id: int):
    await _update_vk_account_group_db(data["groups_data"]["groups"], vk_account_id_database, user_id)
    return data