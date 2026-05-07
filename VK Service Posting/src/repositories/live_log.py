from src.models.live_log import LiveLogOrm
from src.repositories.base import BaseRepository
from src.schemas.live_log import LiveLog


class LiveLogRepository(BaseRepository):
    model = LiveLogOrm
    schema = LiveLog
