from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from src.celery_app import app
from src.models import VKAccountOrm
from src.models.category import CategoryOrm
from src.models.schedule_posting import SchedulePostingOrm
from src.models.vk_group import VKGroupOrm
from src.models.workerpost import WorkerPostOrm
from src.services.live_log import livelogadd_sync
from src.services.workerpost_banner_service import compose_clip_with_banner

from src.vk_api_methods.vk_auth import get_new_token_request
from src.vk_api_methods.vk_posting import upload_short_video, download_clip_by_url, delete_file
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
    flood_time = datetime.now(timezone.utc) + timedelta(minutes=minutes)
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
        print(f"VK Account Name: {vk_account.name}")
        token = get_new_token_request(token_db, cookie_db, proxy)

        clip_filename = download_clip_by_url(clip_url, vk_clip_owner_id, clip_id)
        upload_video_path = clip_filename
        rendered_clip_path = None
        try:
            if workerpost.banner_video_path:
                rendered_clip_path = compose_clip_with_banner(
                    clip_path=clip_filename,
                    banner_video_path=workerpost.banner_video_path,
                    banner_x=workerpost.banner_x,
                    banner_y=workerpost.banner_y,
                    banner_width=workerpost.banner_width,
                    banner_height=workerpost.banner_height,
                    remove_green_background=workerpost.banner_remove_green_background,
                )
                upload_video_path = rendered_clip_path

            upload_short_video(
                token,
                vk_group.vk_group_id,
                upload_video_path,
                category.description,
                category.repost_enabled,
                proxy
            )
            vk_account.account_type = "posting"
        except Exception as e:
            if schedule_update_data:
                session.delete(schedule_update_data)
                session.commit()

            if hasattr(e, "code") and e.code == 9:
                print("VK Flood control error!")
                flood_time = get_flood_control_datetime()
                vk_account.flood_control = True
                vk_account.flood_control_time = flood_time
                session.commit()
                livelogadd_sync(
                    session,
                    workerpost.user_id,
                    "posting",
                    "VK flood control",
                    (
                        f"account_id={vk_account.id}; workerpost_id={workerpost.id}; "
                        f"schedule_id={schedule_database_id}; until={flood_time.isoformat()}"
                    ),
                )

                raise e
            elif hasattr(e, "code") and e.code == 5 and "user is blocked" in str(e).lower():
                print("VK account is blocked!")
                vk_account.account_type = "blocked" # account blocked
                session.commit()
                livelogadd_sync(
                    session,
                    workerpost.user_id,
                    "posting",
                    "Аккаунт заблокирован VK",
                    f"account_id={vk_account.id}; workerpost_id={workerpost.id}; schedule_id={schedule_database_id}",
                )
                raise e

            else:
                raise e
        else:
            if workerpost:
                workerpost.last_post_at = datetime.now()
            if schedule_update_data:
                schedule_update_data.clip_id = clip_id
                schedule_update_data.status = "success"
            session.commit()
            livelogadd_sync(
                session,
                workerpost.user_id,
                "posting",
                "Клип опубликован",
                (
                    f"workerpost_id={workerpost.id}; schedule_id={schedule_database_id}; "
                    f"clip_vk_id={clip_id}; target_group_vk_id={vk_group.vk_group_id}"
                ),
            )
        finally:
            if rendered_clip_path:
                delete_file(rendered_clip_path)
            if clip_filename and clip_filename != rendered_clip_path:
                delete_file(clip_filename)

@app.task
def create_post(worker_id: int, token_db: str, schedule_id: int, clip: dict, proxy: str):
    try:
        posting_clip(worker_id, token_db, schedule_id, clip, proxy)
    except Exception as e:
        print(f"create_post error: {e}")
        is_known_vk_state = hasattr(e, "code") and (
            e.code == 9 or (e.code == 5 and "user is blocked" in str(e).lower())
        )
        if not is_known_vk_state:
            with SyncSessionLocal() as session:
                workerpost = session.execute(
                    select(WorkerPostOrm).where(WorkerPostOrm.id == worker_id)
                ).scalars().one_or_none()
                if workerpost:
                    livelogadd_sync(
                        session,
                        workerpost.user_id,
                        "posting",
                        "Ошибка публикации клипа",
                        f"workerpost_id={worker_id}; schedule_id={schedule_id}; error={e}",
                    )
        #async_to_sync(posting_error)(schedule_id, database_manager)