from src.repositories.base import BaseRepository
from src.models.workerpost import WorkerPostOrm
from src.schemas.workerpost import WorkerPost


class WorkerPostRepository(BaseRepository):
    model = WorkerPostOrm
    schema = WorkerPost