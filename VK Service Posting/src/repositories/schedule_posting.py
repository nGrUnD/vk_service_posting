from src.models.schedule_posting import SchedulePostingOrm
from src.repositories.base import BaseRepository
from src.schemas.schedule_posting import SchedulePosting


class SchedulePostingRepository(BaseRepository):
    model = SchedulePostingOrm
    schema = SchedulePosting