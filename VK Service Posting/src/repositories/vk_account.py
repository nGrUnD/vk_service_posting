from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.repositories.base import BaseRepository
from src.models.vk_account import VKAccountOrm
from src.schemas.vk_account import VKAccount


class VKAccountRepository(BaseRepository):
    model = VKAccountOrm
    schema = VKAccount

    async def get_all_backup_with_creds(self, user_id: int):
        stmt = (
            select(VKAccountOrm)
            .where(VKAccountOrm.user_id == user_id)
            .where(VKAccountOrm.account_type == "backup")
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
