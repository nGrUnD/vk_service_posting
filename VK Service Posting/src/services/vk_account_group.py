from sqlalchemy import select

from src.models import VKAccountGroupOrm, VKAccountOrm, VKGroupOrm
from src.utils.database_manager import DataBaseManager


class VKAccountGroupService:
    def __init__(self, database: DataBaseManager):
        self.database = database

    async def get_all(self, user_id: int, limit: int = 100, offset: int = 0):
        # 1. связующая таблица
        ag_rows = await self.database.session.scalars(
            select(VKAccountGroupOrm)
            .order_by(VKAccountGroupOrm.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        ag_list = ag_rows.all()

        # 2. уникальные id
        acc_ids = {ag.vk_account_id for ag in ag_list}
        grp_ids = {ag.vk_group_id for ag in ag_list}

        # 3. получить аккаунты и группы одним запросом каждый
        acc_list = (await self.database.session.scalars(
            select(VKAccountOrm).where(VKAccountOrm.id.in_(acc_ids))
        )).all()
        grp_list = (await self.database.session.scalars(
            select(VKGroupOrm).where(VKGroupOrm.id.in_(grp_ids))
        )).all()

        acc_map = {a.id: a for a in acc_list}
        grp_map = {g.id: g for g in grp_list}

        # 4. собрать DTO
        result = []
        for ag in ag_list:
            result.append({
                "id": ag.id,
                "vk_account_id": ag.vk_account_id,
                "vk_group_id": ag.vk_group_id,
                "role": ag.role,
                "created_at": ag.created_at,
                "updated_at": ag.updated_at,
                "account": acc_map.get(ag.vk_account_id),
                "group": grp_map.get(ag.vk_group_id),
            })