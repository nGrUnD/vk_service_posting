"""Отзыв Celery-задач по id (в т.ч. тяжёлые Selenium / vk_login)."""
from __future__ import annotations

import logging
import re
from collections.abc import Iterable

from src.celery_app import app as celery_app

_CELERY_TASK_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_PLACEHOLDER_TASK_IDS = frozenset({"", "0", "pending", "curl", "starting", "none", "null"})


def looks_like_celery_task_id(task_id: str | None) -> bool:
    if task_id is None:
        return False
    t = str(task_id).strip()
    if not t or t.lower() in _PLACEHOLDER_TASK_IDS:
        return False
    return bool(_CELERY_TASK_ID_RE.match(t))


def revoke_celery_task_ids(task_ids: Iterable[str | None]) -> None:
    """terminate=True — остановить уже выполняющуюся задачу на воркере (важно для Selenium)."""
    seen: set[str] = set()
    for raw in task_ids:
        if raw is None:
            continue
        tid = str(raw).strip()
        if not looks_like_celery_task_id(tid) or tid in seen:
            continue
        seen.add(tid)
        try:
            celery_app.control.revoke(tid, terminate=True)
        except Exception:
            logging.exception("Celery revoke failed for task_id=%r", tid)
