from src.schemas.celery_task import CeleryTaskAdd
from src.utils.database_manager import DataBaseManager

class CeleryTaskService:
    def __init__(self, database: DataBaseManager):
        self.database = database

    async def create_celery_task_record(self, task_id: str, user_id: int, task_type: str,
                                        vk_account_id: int | None, clip_list_id: int | None,
                                        vk_group_url: str | None,
                                        ):
        celery_task_add = CeleryTaskAdd(
            task_id=task_id,
            user_id=user_id,
            clip_list_id=clip_list_id,
            vk_account_id=vk_account_id,
            vk_group_url=vk_group_url,
            status="in_progress",
            type=task_type,
        )
        await self.database.celery_task.add(celery_task_add)