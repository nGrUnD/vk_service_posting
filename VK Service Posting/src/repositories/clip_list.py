from src.models.clip_list import ClipListOrm
from src.repositories.base import BaseRepository
from src.schemas.clip_list import ClipList


class ClipListRepository(BaseRepository):
    model = ClipListOrm
    schema = ClipList