from functools import wraps
from asgiref.sync import async_to_sync

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from src.schemas.vk_account import VKAccountUpdate
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.repositories.vk_account import VKAccountRepository


async def mark_vk_account_failure_by_task_id(vk_account_id: int):
    engine = create_async_engine(settings.DB_URL, future=True)
    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
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
