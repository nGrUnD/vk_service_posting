from src.repositories.base import BaseRepository
from src.models.vk_group import VKGroupOrm
from src.schemas.vk_group import VKGroup


class VKGroupRepository(BaseRepository):
    model = VKGroupOrm
    schema = VKGroup