"""Синхронные операции с батчами (из Celery / sync engine)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import update

from src.celery_app.celery_db import SyncSessionLocal
from src.models.account_checker_batch import AccountCheckerBatchOrm
from src.services.live_log import livelogadd_sync


def mark_checker_batch_task_done_sync(batch_id: int | None) -> None:
    if batch_id is None:
        return
    try:
        with SyncSessionLocal() as session:
            result = session.execute(
                update(AccountCheckerBatchOrm)
                .where(AccountCheckerBatchOrm.id == int(batch_id))
                .values(
                    completed_tasks=AccountCheckerBatchOrm.completed_tasks + 1,
                )
                .returning(
                    AccountCheckerBatchOrm.completed_tasks,
                    AccountCheckerBatchOrm.total_tasks,
                    AccountCheckerBatchOrm.user_id,
                )
            )
            row = result.one()
            done, total, user_id = int(row[0]), int(row[1]), int(row[2])
            if done >= total and total > 0:
                session.execute(
                    update(AccountCheckerBatchOrm)
                    .where(AccountCheckerBatchOrm.id == int(batch_id))
                    .values(
                        status="completed",
                        completed_at=datetime.now(timezone.utc),
                    )
                )
                logging.info(
                    "Account checker batch %s completed: %s/%s",
                    batch_id,
                    done,
                    total,
                )
                livelogadd_sync(
                    session,
                    user_id,
                    "account_checker",
                    "Проверка аккаунтов: батч завершён",
                    f"batch_id={batch_id}; tasks={done}/{total}",
                )
            session.commit()
    except Exception:
        logging.exception("mark_checker_batch_task_done_sync failed for batch_id=%s", batch_id)
        raise
