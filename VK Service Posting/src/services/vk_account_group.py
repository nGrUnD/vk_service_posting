from sqlalchemy import select, func

from src.models import VKAccountGroupOrm, VKAccountOrm, VKGroupOrm
from src.utils.database_manager import DataBaseManager


class VKAccountGroupService:
    def __init__(self, database: DataBaseManager):
        self.database = database

    async def get_all(self, user_id: int, limit: int = 100, offset: int = 0):
        # Подзапрос для фильтрации связей по user_id (если VKAccountOrm имеет поле user_id)
        # Если фильтрация по пользователю не нужна — уберите join/where и используйте глобальный count.
        base_stmt = (
            select(VKAccountGroupOrm)
            .join(VKAccountOrm, VKAccountOrm.id == VKAccountGroupOrm.vk_account_id)
            .where(VKAccountOrm.user_id == user_id)
        )

        # 0) count всего (без limit/offset)
        total = await self.database.session.scalar(
            select(func.count())
            .select_from(base_stmt.subquery())
        )
        total = total or 0

        # 1) страница данных
        ag_rows = await self.database.session.scalars(
            base_stmt
            .order_by(VKAccountGroupOrm.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        ag_list = ag_rows.all()

        if not ag_list:
            return {"items": [], "count": total}

        # 2) уникальные id
        acc_ids = {ag.vk_account_id for ag in ag_list}
        grp_ids = {ag.vk_group_id for ag in ag_list}

        # 3) батч-загрузка аккаунтов и групп
        acc_map = {}
        if acc_ids:
            acc_list = (await self.database.session.scalars(
                select(VKAccountOrm).where(VKAccountOrm.id.in_(acc_ids))
            )).all()
            acc_map = {a.id: a for a in acc_list}

        grp_map = {}
        if grp_ids:
            grp_list = (await self.database.session.scalars(
                select(VKGroupOrm).where(VKGroupOrm.id.in_(grp_ids))
            )).all()
            grp_map = {g.id: g for g in grp_list}

        # 4) DTO
        items = []
        for ag in ag_list:
            items.append({
                "id": ag.id,
                "vk_account_id": ag.vk_account_id,  # id связующей записи
                "vk_group_id": ag.vk_group_id,
                "role": ag.role,
                "created_at": ag.created_at,
                "updated_at": ag.updated_at,
                "account": acc_map.get(ag.vk_account_id),
                "group": grp_map.get(ag.vk_group_id),
            })

        return {"items": items, "count": total}