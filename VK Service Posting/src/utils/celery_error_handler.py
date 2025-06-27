from functools import wraps
from asgiref.sync import async_to_sync
from sqlalchemy import select

from src.celery_app.celery_db import SyncSessionLocal
from src.models.vk_account import VKAccountOrm


def mark_vk_account_failure_by_task_id(vk_account_id: int):
    with SyncSessionLocal() as session:
        stmt = select(VKAccountOrm).where(VKAccountOrm.id == vk_account_id)
        result = session.execute(stmt)
        account = result.scalars().one_or_none()
        account.parse_status = "failure"
        print(f"vk_account: {vk_account_id}")
        session.commit()


def celery_task_with_db_failure_status(update_status_by_task_id_fn):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                print(f"[CeleryError] Task failed: {e}")
                try:
                    vk_account_id = kwargs.get("vk_account_id")
                    if vk_account_id is not None:
                        update_status_by_task_id_fn(vk_account_id)
                except Exception as inner:
                    print(f"[DB update failure] Could not mark task_id failure: {inner}")
                raise e
        return wrapper
    return decorator
