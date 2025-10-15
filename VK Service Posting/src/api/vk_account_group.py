from fastapi import APIRouter, HTTPException, status, Body

from src.api.dependencies import UserIdDep, DataBaseDep
from src.services.vk_account_group import VKAccountGroupService

router = APIRouter(prefix="/users/{user_id}/vk_account_group", tags=["VK Аккаунты и Паблики"])

@router.get("/all", summary="Получить все VK аккаунты пользователя")
async def get_all_vk_accounts_groups(
        limit: int,
        offset: int,
        user_id: UserIdDep,
        database: DataBaseDep,
):
    if offset < 0:
        offset = 0

    return await VKAccountGroupService(database).get_all(user_id, limit, offset)