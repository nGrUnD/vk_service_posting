from sqlalchemy import select

from src.celery_app import app
from src.models.category import CategoryOrm
from src.models.schedule_posting import SchedulePostingOrm
from src.models.vk_group import VKGroupOrm
from src.models.workerpost import WorkerPostOrm

from src.schemas.schedule_posting import SchedulePostingUpdate
from src.vk_api.vk_posting import download_vk_clip, upload_short_video, get_clip_info, delete_file
from src.celery_app.celery_db import SyncSessionLocal


async def posting_error(schedule_database_id: int, database_manager):
    async with database_manager as database:
        schedule_update_data = SchedulePostingUpdate(
            status = "failed",
        )
        await database.schedule_posting.edit(schedule_update_data, exclude_unset=True, id=schedule_database_id)
        await database.commit()

def posting_clip(worker_id: int, token: str, schedule_database_id: int, clip, proxy: str):
    with SyncSessionLocal() as session:
        stmt = select(WorkerPostOrm).where(WorkerPostOrm.id == worker_id)
        result = session.execute(stmt)
        workerpost = result.scalars().one_or_none()

        stmt = select(CategoryOrm).where(CategoryOrm.id == workerpost.category_id)
        result = session.execute(stmt)
        category = result.scalars().one_or_none()

        stmt = select(VKGroupOrm).where(VKGroupOrm.id == workerpost.vk_group_id)
        result = session.execute(stmt)
        vk_group = result.scalars().one_or_none()


        stmt = select(VKGroupOrm).where(VKGroupOrm.id == clip['vk_group_id'])
        result = session.execute(stmt)
        vk_group_source = result.scalars().one_or_none()

        vk_clip_owner_id = -vk_group_source.vk_group_id
        clip_id = clip['vk_id']
        new_clip_data_files = get_clip_info(vk_clip_owner_id, clip_id, token, proxy)

        files = new_clip_data_files['files']

        clip_filename = download_vk_clip(files, vk_clip_owner_id, clip_id, proxy)

        upload_short_video(
            token,
            vk_group.vk_group_id,
            clip_filename,
            category.description,
            category.repost_enabled,
            proxy
        )

        delete_file(clip_filename)

        stmt = select(SchedulePostingOrm).where(SchedulePostingOrm.id == schedule_database_id)
        result = session.execute(stmt)
        schedule_update_data = result.scalars().one_or_none()

        schedule_update_data.clip_id = clip_id
        schedule_update_data.status = "success"

        session.commit()

@app.task
def create_post(worker_id: int, token: str, schedule_id: int, clip, proxy: str):
    try:
        posting_clip(worker_id, token, schedule_id, clip, proxy)
    except Exception as e:
        print(f"create_post error: {e}")
        #async_to_sync(posting_error)(schedule_id, database_manager)