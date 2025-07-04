from typing import Optional

from sqlalchemy import select, func

from src.models.vk_clip import VKClipOrm
from src.repositories.base import BaseRepository
from src.schemas.vk_clip import VKClip


class VKClipRepository(BaseRepository):
    model = VKClipOrm
    schema = VKClip

    async def get_random_one(self, clip_list_id: int) -> Optional[VKClipOrm]:
        stmt = (
            select(VKClipOrm)
            .where(VKClipOrm.clip_list_id == clip_list_id)
            .order_by(func.random())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()