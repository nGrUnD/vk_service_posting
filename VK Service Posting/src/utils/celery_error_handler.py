from functools import wraps
from asgiref.sync import async_to_sync

from src.schemas.vk_account import VKAccountUpdate
from src.repositories.vk_account import VKAccountRepository
from src.celery_app.celery_db import AsyncSessionLocal


async def mark_vk_account_failure_by_task_id(vk_account_id: int):
    async with AsyncSessionLocal() as session:
        repo = VKAccountRepository(session)
        data = {
            "parse_status": "failure"
        }
        data_update = VKAccountUpdate(**data)
        print(f"vk_account: {vk_account_id}")
        await repo.edit(data_update, exclude_unset=True, id=vk_account_id)

        await session.commit()
    AsyncSessionLocal.close_all()


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
                        async_to_sync(update_status_by_task_id_fn)(vk_account_id)
                except Exception as inner:
                    print(f"[DB update failure] Could not mark task_id failure: {inner}")
                raise e
        return wrapper
    return decorator
