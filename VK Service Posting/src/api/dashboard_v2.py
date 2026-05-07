"""Эндпоинты дашборда V2: активность постинга и лента событий."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query
from sqlalchemy import desc, select

from src.api.dependencies import DataBaseDep, UserIdDep
from src.models.celery_task import CeleryTaskOrm
from src.models.live_log import LiveLogOrm
from src.models.proxy import ProxyOrm
from src.models.schedule_posting import SchedulePostingOrm
from src.models.vk_account import VKAccountOrm
from src.models.vk_group import VKGroupOrm
from src.models.workerpost import WorkerPostOrm

router = APIRouter(prefix="/users/{user_id}/dashboard", tags=["Dashboard V2"])


def _floor_hour_utc(dt: datetime) -> datetime:
    dt = dt.astimezone(timezone.utc)
    return dt.replace(minute=0, second=0, microsecond=0)


def _iso_utc(dt: datetime | None) -> str | None:
    if not dt:
        return None
    return dt.astimezone(timezone.utc).isoformat()


def _task_group(task_type: str | None) -> str:
    task_type_l = (task_type or "").lower()
    if "account" in task_type_l:
        return "account"
    if "group" in task_type_l or "source" in task_type_l:
        return "group"
    if "clip" in task_type_l:
        return "clip"
    return "task"


@router.get("/v2/posting_activity", summary="Почасовое число успешных постов за последние N часов")
async def v2_posting_activity(
        user_id: UserIdDep,
        database: DataBaseDep,
        hours: int = Query(24, ge=1, le=168),
):
    now_floor = _floor_hour_utc(datetime.now(timezone.utc))
    since = now_floor - timedelta(hours=hours - 1)

    stmt = (
        select(
            SchedulePostingOrm.created_at,
        )
        .select_from(SchedulePostingOrm)
        .join(WorkerPostOrm, WorkerPostOrm.id == SchedulePostingOrm.workpost_id)
        .where(
            WorkerPostOrm.user_id == user_id,
            SchedulePostingOrm.status == "success",
            SchedulePostingOrm.created_at >= since,
        )
    )

    result = await database.session.execute(stmt)
    rows = result.scalars().all()

    db_counts: dict[int, int] = {}
    for created_at in rows:
        if created_at is None:
            continue
        h = _floor_hour_utc(created_at)
        hk = int(h.timestamp()) // 3600
        db_counts[hk] = db_counts.get(hk, 0) + 1

    buckets = []
    for i in range(hours):
        slot = now_floor - timedelta(hours=(hours - 1 - i))
        hk = int(slot.timestamp()) // 3600
        buckets.append({
            "hour_start": slot.isoformat(),
            "posted": db_counts.get(hk, 0),
        })

    return {"hours": hours, "buckets": buckets}


@router.get("/v2/activity_log", summary="Последние события для живого лога")
async def v2_activity_log(
        user_id: UserIdDep,
        database: DataBaseDep,
        limit: int = Query(25, ge=1, le=100),
        groups: list[str] | None = Query(default=None),
):
    base_allowed_groups = {"post", "worker", "account", "group", "clip", "proxy", "task"}

    manual_stmt = (
        select(
            LiveLogOrm.created_at,
            LiveLogOrm.logtype,
            LiveLogOrm.log,
            LiveLogOrm.logdescription,
            LiveLogOrm.id,
        )
        .where(LiveLogOrm.user_id == user_id)
        .order_by(desc(LiveLogOrm.created_at))
        .limit(limit * 3)
    )
    manual_rows = (await database.session.execute(manual_stmt)).all()
    manual_groups = {
        (logtype or "manual").strip().lower()
        for _, logtype, _, _, _ in manual_rows
        if (logtype or "").strip()
    }
    allowed_groups = base_allowed_groups | manual_groups
    selected_groups = {
        g.strip().lower()
        for g in (groups or [])
        if g and g.strip().lower() in allowed_groups
    }
    if not selected_groups:
        selected_groups = allowed_groups.copy()

    items = []

    # Ручные live-log события из backend-кода через livelogadd(...)
    for created_at, logtype, log, logdescription, log_id in manual_rows:
        group = (logtype or "manual").strip().lower() or "manual"
        items.append({
            "at": _iso_utc(created_at),
            "status": group,
            "group": group,
            "message": log,
            "description": logdescription,
            "logdescription": logdescription,
            "live_log_id": log_id,
        })

    # Постинг (schedule_posting)
    post_stmt = (
        select(
            SchedulePostingOrm.created_at,
            SchedulePostingOrm.status,
            VKGroupOrm.name.label("group_name"),
            WorkerPostOrm.id.label("workerpost_id"),
        )
        .select_from(SchedulePostingOrm)
        .join(WorkerPostOrm, WorkerPostOrm.id == SchedulePostingOrm.workpost_id)
        .join(VKGroupOrm, VKGroupOrm.id == WorkerPostOrm.vk_group_id)
        .where(WorkerPostOrm.user_id == user_id)
        .order_by(desc(SchedulePostingOrm.created_at))
        .limit(limit * 3)
    )
    post_rows = (await database.session.execute(post_stmt)).all()
    for created_at, status, group_name, wp_id in post_rows:
        items.append({
            "at": _iso_utc(created_at),
            "status": status,
            "group": "post",
            "message": f"Публикация в «{group_name or '—'}» ({status})",
            "group_name": group_name or "—",
            "workerpost_id": wp_id,
        })

    # Celery-задачи (парсинг аккаунтов/групп/клипов и прочее)
    task_stmt = (
        select(
            CeleryTaskOrm.created_at,
            CeleryTaskOrm.status,
            CeleryTaskOrm.type,
            CeleryTaskOrm.task_id,
        )
        .where(CeleryTaskOrm.user_id == user_id)
        .order_by(desc(CeleryTaskOrm.created_at))
        .limit(limit * 3)
    )
    task_rows = (await database.session.execute(task_stmt)).all()
    for created_at, status, task_type, task_id in task_rows:
        g = _task_group(task_type)
        items.append({
            "at": _iso_utc(created_at),
            "status": status,
            "group": g,
            "message": f"Задача: {task_type or 'unknown'} ({status or 'unknown'})",
            "task_id": task_id,
        })

    # Изменения воркеров
    worker_stmt = (
        select(
            WorkerPostOrm.updated_at,
            WorkerPostOrm.is_active,
            WorkerPostOrm.id,
        )
        .where(WorkerPostOrm.user_id == user_id)
        .order_by(desc(WorkerPostOrm.updated_at))
        .limit(limit * 2)
    )
    worker_rows = (await database.session.execute(worker_stmt)).all()
    for updated_at, is_active, wp_id in worker_rows:
        items.append({
            "at": _iso_utc(updated_at),
            "status": "active" if is_active else "paused",
            "group": "worker",
            "message": f"Воркер #{wp_id} {'активен' if is_active else 'остановлен'}",
            "workerpost_id": wp_id,
        })

    # Изменения аккаунтов (удобно видеть свежие parse/flood события)
    account_stmt = (
        select(
            VKAccountOrm.updated_at,
            VKAccountOrm.parse_status,
            VKAccountOrm.name,
            VKAccountOrm.second_name,
            VKAccountOrm.id,
        )
        .where(VKAccountOrm.user_id == user_id)
        .order_by(desc(VKAccountOrm.updated_at))
        .limit(limit * 2)
    )
    account_rows = (await database.session.execute(account_stmt)).all()
    for updated_at, parse_status, name, second_name, account_id in account_rows:
        full_name = f"{name or ''} {second_name or ''}".strip() or f"Аккаунт #{account_id}"
        items.append({
            "at": _iso_utc(updated_at),
            "status": parse_status,
            "group": "account",
            "message": f"{full_name}: статус {parse_status or 'unknown'}",
            "vk_account_id": account_id,
        })

    # Прокси
    proxy_stmt = (
        select(
            ProxyOrm.updated_at,
            ProxyOrm.http,
            ProxyOrm.id,
        )
        .where(ProxyOrm.user_id == user_id)
        .order_by(desc(ProxyOrm.updated_at))
        .limit(limit * 2)
    )
    proxy_rows = (await database.session.execute(proxy_stmt)).all()
    for updated_at, http, proxy_id in proxy_rows:
        items.append({
            "at": _iso_utc(updated_at),
            "status": "updated",
            "group": "proxy",
            "message": f"Прокси #{proxy_id}: {http}",
            "proxy_id": proxy_id,
        })

    filtered = [item for item in items if item.get("group") in selected_groups]
    filtered.sort(key=lambda item: item.get("at") or "", reverse=True)
    filtered = filtered[:limit]

    return {
        "items": filtered,
        "groups_available": sorted(allowed_groups),
        "groups_selected": sorted(selected_groups),
    }
