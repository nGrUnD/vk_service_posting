import re
from typing import Dict, Optional, List

from sqlalchemy import select

from src.celery_app import app
from datetime import datetime, timezone

from src.models.celery_task import CeleryTaskOrm
from src.models.vk_clip import VKClipOrm
from src.vk_api_methods.vk_clip import get_all_owner_short_videos
from src.celery_app.celery_db import SyncSessionLocal


def best_quality_key(files: Dict[str, str]) -> Optional[str]:
    best_k = None
    best_res = -1

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
    if 'hls' in files:
        return 'hls'
    return next(iter(files), None)


def update_vk_clips_db(clips: List[dict], user_id: int, clip_list_id: int, task_id: int, vk_group_database_id: int):
    with SyncSessionLocal() as session:
        # 1. Получаем объект задачи Celery
        stmt = select(CeleryTaskOrm).where(CeleryTaskOrm.task_id == task_id)
        celery_task = session.execute(stmt).scalars().one_or_none()

        if not clips:
            if celery_task:
                celery_task.status = "empty"
                session.commit()
            return

        # 2. Получаем уже существующие vk_id по этой группе
        existing_stmt = select(VKClipOrm.vk_id).where(VKClipOrm.vk_group_id == vk_group_database_id)
        existing_vk_ids = {row[0] for row in session.execute(existing_stmt).all()}

        # 3. Готовим список новых объектов
        new_clips = []

        for clip_data in clips:
            vk_id = clip_data.get("id")
            if not vk_id or vk_id in existing_vk_ids:
                continue

            files = clip_data.get("files", {})
            if not files:
                continue

            best_key = best_quality_key(files)
            if not best_key:
                continue

            file_url = files.get(best_key)
            if not file_url:
                continue

            date_ts = clip_data.get("date")
            views = clip_data.get("views", 0)

            try:
                dt = datetime.fromtimestamp(date_ts)
            except Exception:
                continue

            new_clips.append(VKClipOrm(
                user_id=user_id,
                clip_list_id=clip_list_id,
                vk_group_id=vk_group_database_id,
                vk_id=vk_id,
                files=file_url,
                views=views,
                date=dt,
                frames_file="",  # опционально можно сюда timeline_thumbs
                parse_status="success",
                task_id=""
            ))

        # 4. Массовая вставка
        if new_clips:
            session.bulk_save_objects(new_clips)

        # 5. Обновляем статус задачи
        if celery_task:
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
def parse_vk_group_clips_sync(self, vk_group_id: int, login: str, password: str, token_db: str, cookie_db, proxy: str,
                              user_id: int, clip_list_id: int, vk_group_database_id: int, viewers: int,
                              mindate: datetime):
    task_id = self.request.id
    try:
        # Важно: в ВК id паблика с минусом для публичных групп
        owner_id = -vk_group_id if not str(vk_group_id).startswith("-") else vk_group_id
        clips = get_all_owner_short_videos(owner_id, login, password, token_db, cookie_db, proxy)

        filtred_clips = filter_clips(clips, viewers, mindate)

        # Асинхронно обновляем БД
        update_vk_clips_db(filtred_clips, user_id, clip_list_id, task_id, vk_group_database_id)

    except Exception as e:
        def update_status_failure():
            with SyncSessionLocal() as session:
                stmt = select(CeleryTaskOrm).where(CeleryTaskOrm.task_id == task_id)
                result = session.execute(stmt)
                celery_task = result.scalars().one_or_none()
                if celery_task:
                    celery_task.status = "failed"
                    session.commit()

        update_status_failure()
        raise e
