from src.models.celery_task import CeleryTaskOrm
from src.repositories.base import BaseRepository
from src.schemas.celery_task import CeleryTask


class CeleryTaskRepository(BaseRepository):
    model = CeleryTaskOrm
    schema = CeleryTask