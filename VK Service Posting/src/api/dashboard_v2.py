"""Эндпоинты дашборда V2: активность постинга и лента событий."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query
from sqlalchemy import desc, select

from src.api.dependencies import DataBaseDep, UserIdDep
from src.models.schedule_posting import SchedulePostingOrm
from src.models.vk_group import VKGroupOrm
from src.models.workerpost import WorkerPostOrm

router = APIRouter(prefix="/users/{user_id}/dashboard", tags=["Dashboard V2"])


def _floor_hour_utc(dt: datetime) -> datetime:
    dt = dt.astimezone(timezone.utc)
    return dt.replace(minute=0, second=0, microsecond=0)


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


@router.get("/v2/activity_log", summary="Последние события постинга для живого лога")
async def v2_activity_log(
        user_id: UserIdDep,
        database: DataBaseDep,
        limit: int = Query(25, ge=1, le=100),
):
    stmt = (
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
        .limit(limit)
    )

    result = await database.session.execute(stmt)
    rows = result.all()

    items = []
    for created_at, status, group_name, wp_id in rows:
        items.append({
            "at": created_at.isoformat() if created_at else None,
            "status": status,
            "group_name": group_name or "—",
            "workerpost_id": wp_id,
        })

    return {"items": items}
