from src.models.vk_account_group import VKAccountGroupOrm
from src.repositories.base import BaseRepository
from src.schemas.vk_account_group import VKAccountGroup


class VKAccountGroupRepository(BaseRepository):
    model = VKAccountGroupOrm
    schema = VKAccountGroup