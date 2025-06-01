from fastapi import APIRouter, HTTPException, status, Body

from src.api.dependencies import DataBaseDep, UserIdDep
from src.schemas.vk_group import VKGroupRequestAddUrl
from src.services.vk_group_service import VKGroupSourceService

router = APIRouter(prefix="/users/{user_id}/vk_group", tags=["VK Группы | Сообщества"])


@router.get("/all", summary="Получить все VK группы пользователя")
async def get_all_vk_groups(
        user_id: UserIdDep,
        database: DataBaseDep,
):
    return await database.vk_group.get_all_filtered(user_id=user_id)

@router.get("/vk_groups_source", summary="Получить все VK группы пользователя Источники")
async def get_all_vk_groups_source(
        user_id: UserIdDep,
        database: DataBaseDep,
):
    """Возвращает все привязанные VK аккаунты пользователя"""
    return await database.vk_account.get_all_filtered(account_type="backup", user_id=user_id)

@router.get("/vk_groups_poster", summary="Получить все VK группы пользователя Постинг")
async def get_all_vk_groups_poster(
        user_id: UserIdDep,
        database: DataBaseDep,
):
    """Возвращает все привязанные VK аккаунты пользователя"""
    return await database.vk_account.get_all_filtered(account_type="poster", user_id=user_id)


@router.get("/{vk_group_id}", summary="Получить конкретный VK паблик | группу")
async def get_vk_group(
        user_id: UserIdDep,
        vk_group_id: int,
        database: DataBaseDep,
):
    """Возвращает детальную информацию о конкретном VK аккаунте"""
    account = await database.vk_group.get_one_or_none(
        id=vk_group_id,
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VK паблик не найден"
        )

    return account

@router.get("/{vk_group_id}/status", summary="Статус парсинга VK паблика")
async def get_vk_group_status(
      user_id: UserIdDep,
      vk_group_id: int,
      database: DataBaseDep,
):
    account = await database.vk_group.get_one_or_none(id=vk_group_id)
    if not account:
        raise HTTPException(404, "Не найден VK паблик")
    return {
        "status": account.parse_status,   # pending | success | failure
        "task_id": account.task_id,
    }


@router.post("/create_groups", status_code=status.HTTP_201_CREATED, summary="Добавить сразу много групп Источников по url")
async def create_vk_accounts(
        user_id: UserIdDep,
        database: DataBaseDep,
        vk_groups_request: VKGroupRequestAddUrl,
):
    """Добавляет новый VK аккаунт для парсинга данных"""
    user = await database.user.get_one_or_none(id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )

    if not vk_groups_request.date_range and not vk_groups_request.parse_all:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Не указана дата окончания при parse_all=False"
        )

    try:
        detail = await VKGroupSourceService(database).create_groups(user_id, vk_groups_request)
        #detail = await VKAccountBackupService(database).create_accounts(user_id, groups_url)
        return {"status": "OK", "detail": detail}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{vk_group_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить VK паблик")
async def delete_vk_group(
        user_id: UserIdDep,
        vk_group_id: int,
        database: DataBaseDep,
):
    """Удаляет привязанный VK аккаунт и связанные данные"""
    await database.vk_group.delete(id=vk_group_id, user_id=user_id)
    await database.commit()

    return {"status": "OK"}
