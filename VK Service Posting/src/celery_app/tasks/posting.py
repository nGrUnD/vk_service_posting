from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.celery_app import app
from asgiref.sync import async_to_sync

from src.config import settings
from src.schemas.schedule_posting import SchedulePostingUpdate
from src.utils.database_manager import DataBaseManager
from src.vk_api.vk_posting import download_vk_clip, upload_short_video, get_clip_info, delete_file


async def posting_error(schedule_database_id: int):
    engine = create_async_engine(settings.DB_URL, future=True)
    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    database_manager = DataBaseManager(AsyncSessionLocal)
    async with database_manager as database:
        schedule_update_data = SchedulePostingUpdate(
            status = "failed",
        )
        await database.schedule_posting.edit(schedule_update_data, exclude_unset=True, id=schedule_database_id)
        await database.commit()

async def posting_clip(worker_id: int, token: str, schedule_database_id: int, clip):
    engine = create_async_engine(settings.DB_URL, future=True)
    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    database_manager = DataBaseManager(AsyncSessionLocal)
    async with database_manager as database:
        workerpost = await database.workerpost.get_one_or_none(id=worker_id)
        category = await database.category.get_one_or_none(id=workerpost.category_id)
        vk_group = await database.vk_group.get_one_or_none(id=workerpost.vk_group_id)
        vk_group_source = await database.vk_group.get_one_or_none(id=clip['vk_group_id'])

        vk_clip_owner_id = -vk_group_source.vk_group_id
        clip_id = clip['vk_id']
        new_clip_data_files = get_clip_info(vk_clip_owner_id, clip_id, token)

        files = new_clip_data_files['files']

        clip_filename = download_vk_clip(files, vk_clip_owner_id, clip_id)

        upload_short_video(
            token,
            vk_group.vk_group_id,
            clip_filename,
            category.description,
            category.repost_enabled
        )

        delete_file(clip_filename)

        schedule_update_data = SchedulePostingUpdate(
            clip_id = clip_id,
            status = "success",
        )

        await database.schedule_posting.edit(schedule_update_data, exclude_unset=True, id=schedule_database_id)
        await database.commit()

@app.task
def create_post(worker_id: int, token: str, schedule_id: int, clip):
    try:
        async_to_sync(posting_clip)(worker_id, token, schedule_id, clip)
    except Exception as e:
        print(f"create_post error: {e}")
        async_to_sync(posting_error)(schedule_id)