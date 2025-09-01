from datetime import datetime, timedelta

from sqlalchemy import select
from src.celery_app import app
from src.models import VKAccountOrm
from src.models.category import CategoryOrm
from src.models.schedule_posting import SchedulePostingOrm
from src.models.vk_group import VKGroupOrm
from src.models.workerpost import WorkerPostOrm
from src.utils.cookiejar import list_to_cookiejar

from src.vk_api_methods.vk_auth import get_token, get_new_token, get_new_token_request
from src.vk_api_methods.vk_posting import upload_short_video, download_clip_by_url
from src.celery_app.celery_db import SyncSessionLocal


def posting_error(schedule_database_id: int, database_manager):
    with SyncSessionLocal() as session:
        #schedule_update_data = SchedulePostingUpdate(
        #    status = "failed",
        #)
        #session.schedule_posting.edit(schedule_update_data, exclude_unset=True, id=schedule_database_id)
        session.commit()


def get_flood_control_datetime(minutes=90):
    """Устанавливает flood control на указанное количество минут"""
    flood_time = datetime.now() + timedelta(minutes=minutes)
    return flood_time

def posting_clip(worker_id: int, token_db: str, schedule_database_id: int, clip, proxy: str):
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

        stmt = select(VKAccountOrm).where(VKAccountOrm.id == workerpost.vk_account_id)
        result = session.execute(stmt)
        vk_account = result.scalars().one_or_none()

        stmt = select(VKGroupOrm).where(VKGroupOrm.id == clip['vk_group_id'])
        result = session.execute(stmt)
        vk_group_source = result.scalars().one_or_none()

        stmt = select(SchedulePostingOrm).where(SchedulePostingOrm.id == schedule_database_id)
        result = session.execute(stmt)
        schedule_update_data = result.scalars().one_or_none()

        vk_clip_owner_id = -vk_group_source.vk_group_id
        clip_id = clip['vk_id']
        #new_clip_data_files = get_clip_info(vk_clip_owner_id, clip_id, token, proxy)

        #files = new_clip_data_files['files']

        clip_url = f"https://vk.com/video{vk_clip_owner_id}_{clip_id}"

        #token = get_token(login, password, proxy)

        cookie_db = vk_account.cookies
        #cookie = list_to_cookiejar(cookie_db)
        token = get_new_token_request(token_db, cookie_db, proxy)

        clip_filename = download_clip_by_url(clip_url, vk_clip_owner_id, clip_id)
        try:
            upload_short_video(
                token,
                vk_group.vk_group_id,
                clip_filename,
                category.description,
                category.repost_enabled,
                proxy
            )
        except Exception as e:
            schedule_update_data.status = "error"
            session.commit()

            if hasattr(e, "code") and e.code == 9:
                print("VK Flood control error!")
                flood_time = get_flood_control_datetime()
                vk_account.flood_control = True
                vk_account.flood_control_time = flood_time
                session.commit()

                raise e
            else:
                raise e



        #schedule_update_data.clip_id = clip_id
        schedule_update_data.status = "success"

        session.commit()

@app.task
def create_post(worker_id: int, token_db: str, schedule_id: int, clip: dict, proxy: str):
    try:
        posting_clip(worker_id, token_db, schedule_id, clip, proxy)
    except Exception as e:
        print(f"create_post error: {e}")
        #async_to_sync(posting_error)(schedule_id, database_manager)