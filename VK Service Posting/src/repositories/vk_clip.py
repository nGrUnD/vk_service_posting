from src.models.vk_clip import VKClipOrm
from src.repositories.base import BaseRepository
from src.schemas.vk_clip import VKClip


class VKClipRepository(BaseRepository):
    model = VKClipOrm
    schema = VKClip