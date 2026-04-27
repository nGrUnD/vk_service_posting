from sqlalchemy import insert

from src.repositories.base import BaseRepository
from src.models.account_checker_batch import AccountCheckerBatchOrm
from src.schemas.account_checker_batch import AccountCheckerBatchIn, AccountCheckerBatchOut


class AccountCheckerBatchRepository(BaseRepository):
    model = AccountCheckerBatchOrm
    schema = AccountCheckerBatchOut

    async def create(self, data: AccountCheckerBatchIn) -> AccountCheckerBatchOut:
        add_data_stmt = (
            insert(self.model)
            .values(**data.model_dump())
            .returning(self.model)
        )
        result = await self.session.execute(add_data_stmt)
        model = result.scalars().one()
        return self.schema.model_validate(model)
