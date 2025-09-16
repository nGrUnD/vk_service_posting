from datetime import datetime

from sqlalchemy import func, select
from src.models.schedule_posting import SchedulePostingOrm
from src.repositories.base import BaseRepository
from src.schemas.schedule_posting import SchedulePosting


class SchedulePostingRepository(BaseRepository):
    model = SchedulePostingOrm
    schema = SchedulePosting

    async def count_filtered(self, **filters) -> int:
        query = select(func.count(self.model.id))

        # Строим WHERE условия
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.where(getattr(self.model, key) == value)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_last_posted_date(self, **filters) -> datetime | None:
        query = select(func.max(self.model.created_at))

        # Строим WHERE условия
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.where(getattr(self.model, key) == value)

        result = await self.session.execute(query)
        return result.scalar()
