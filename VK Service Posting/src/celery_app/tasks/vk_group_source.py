import re
from typing import Dict, Optional, List

from asgiref.sync import async_to_sync
from sqlalchemy import select

from src.celery_app import app
from datetime import datetime, timezone

from src.models.celery_task import CeleryTaskOrm
from src.models.vk_clip import VKClipOrm
from src.repositories.celery_task import CeleryTaskRepository
from src.repositories.vk_clip import VKClipRepository
from src.schemas.celery_task import CeleryTaskUpdate
from src.schemas.vk_clip import VKClipAdd
from src.vk_api.vk_clip import get_all_owner_short_videos
from src.celery_app.celery_db import SyncSessionLocal


def best_quality_key(files: Dict[str, str]) -> Optional[str]:
    """
    Из словаря files выбирает ключ с наибольшим разрешением (mp4_NN).
    Если mp4_* ключей нет — возвращает 'hls' (если есть), иначе первый ключ.

    :param files: dict, например {
        'mp4_144': '…', 'mp4_240': '…', 'hls': '…', …
    }
    :return: ключ с наибольшим NN, например 'mp4_480'
    """
    best_k = None
    best_res = -1

    # Ищём все mp4_{число} ключи
    for k in files:
        m = re.match(r'^mp4_(\d+)$', k)
        if not m:
            continue
        res = int(m.group(1))
        if res > best_res:
            best_res = res
            best_k = k

    if best_k:
        return best_k

    # fallback: если нет mp4_*, берём hls, если есть
    if 'hls' in files:
        return 'hls'

    # иначе просто первый ключ
    return next(iter(files), None)


def _add_or_edit_vk_clips_db(session, vk_clip_data: dict, user_id: int,
                             clip_list_id: int, vk_group_database_id: int):
    print(f"group data: {vk_clip_data}")
    vk_id = vk_clip_data["id"]
    best_key = best_quality_key(vk_clip_data["files"])
    files = vk_clip_data["files"][best_key]
    date = datetime.fromtimestamp(vk_clip_data["date"])
    views = vk_clip_data["views"]
    # frames = vk_clip_data["timeline_thumbs"]["links"][0]
    frames = ""

    stmt = select(VKClipOrm).where(VKClipOrm.vk_id == vk_id, VKClipOrm.vk_group_id == vk_group_database_id)
    result = session.execute(stmt)
    get_vk_clip = result.scalars().one_or_none()

    if not get_vk_clip:
        group_new = VKClipOrm(
            user_id=user_id,
            clip_list_id=clip_list_id,
            vk_group_id=vk_group_database_id,
            vk_id=vk_id,
            files=files,
            views=views,
            date=date,
            frames_file=frames,
            parse_status="success",
            task_id=""
        )
        session.add(group_new)


def update_vk_clips_db(clips, user_id, clip_list_id, task_id: int, vk_group_database_id: int):
    with SyncSessionLocal() as session:
        stmt = select(CeleryTaskOrm).where(CeleryTaskOrm.task_id == task_id)
        result = session.execute(stmt)
        celery_task = result.scalars().one_or_none()

        if not clips:
            celery_task.status = "empty"
            session.commit()
            return

        for clip in clips:
            _add_or_edit_vk_clips_db(session, clip, user_id, clip_list_id, vk_group_database_id)

        celery_task.status = "success"
        session.commit()


def filter_clips(clips: List[Dict], min_views: int, published_after: Optional[datetime] = None) -> List[Dict]:
    """
    Фильтрует клипы по минимальному числу просмотров и дате публикации.

    :param clips: Список клипов (dict с ключами "views", "date" и т.п.)
    :param min_views: Минимальное число просмотров
    :param published_after: Только клипы, опубликованные после этой даты (если задано)
    :return: Отфильтрованный список клипов
    """
    filtered = []

    for clip in clips:
        views = clip.get("views", 0)
        timestamp = clip.get("date")
        if not timestamp:
            continue

        clip_date = datetime.fromtimestamp(timestamp, tz=timezone.utc)

        if views >= min_views and (published_after is None or clip_date >= published_after):
            filtered.append(clip)

    return filtered


@app.task(bind=True, name="src.tasks.parse_vk_group_clips_sync")
def parse_vk_group_clips_sync(self, vk_group_id: int, access_token: str,
                              user_id: int, clip_list_id: int, vk_group_database_id: int, viewers: int,
                              mindate: datetime):
    task_id = self.request.id
    try:
        # Важно: в ВК id паблика с минусом для публичных групп
        owner_id = -vk_group_id if not str(vk_group_id).startswith("-") else vk_group_id

        clips = get_all_owner_short_videos(owner_id, access_token)

        filtred_clips = filter_clips(clips, viewers, mindate)

        # Асинхронно обновляем БД
        update_vk_clips_db(filtred_clips, user_id, clip_list_id, task_id, vk_group_database_id)

    except Exception as e:
        def update_status_failure():
            with SyncSessionLocal() as session:
                stmt = select(CeleryTaskOrm).where(CeleryTaskOrm.task_id == task_id)
                result = session.execute(stmt)
                celery_task = result.scalars().one_or_none()

                celery_task.status = "failed"
                session.commit()

        update_status_failure()
        raise e
