from sqlalchemy import select

from src.repositories.base import BaseRepository
from src.models.vk_account_cred import VKAccountCredOrm
from src.schemas.vk_account_cred import VKAccountCred


class VKAccountCredRepository(BaseRepository):
    model = VKAccountCredOrm
    schema = VKAccountCred

    async def get_by_id(self, cred_id: int) -> VKAccountCredOrm | None:
        """
        Возвращает объект VKAccountCredOrm по первичному ключу или None, если не найден.
        """
        return await self.session.get(self.model, cred_id)