from fastapi import APIRouter, HTTPException, status, Body

from src.api.dependencies import DataBaseDep, UserIdDep
from src.schemas.workerpost import WorkerPostRequestAdd
from src.services.workerpost_service import WorkerPostService

router = APIRouter(prefix="/users/{user_id}/workerpost", tags=["VK Постинг"])


@router.get("/all", summary="Получить все VK постинги")
async def get_all_workerpost(
        user_id: UserIdDep,
        database: DataBaseDep,
):
    return await WorkerPostService(database).get_workpost_all(user_id)

@router.get("/{workerpost_id}", summary="Получить конкретный VK постинг")
async def get_workerpost(
        user_id: UserIdDep,
        database: DataBaseDep,
        workerpost_id: int,
):
    """Возвращает детальную информацию о конкретном VK аккаунте"""
    workerpost = await database.workerpost.get_one_or_none(
        id=workerpost_id,
    )

    if not workerpost:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VK постинг не найден"
        )

    return workerpost

@router.get("/{workerpost_id}/status", summary="Статус парсинга VK Постинг")
async def get_vk_group_status(
      user_id: UserIdDep,
      workerpost_id: int,
      database: DataBaseDep,
):
    workerpost = await database.workerpost.get_one_or_none(id=workerpost_id)
    if not workerpost:
        raise HTTPException(404, "Не найден VK постинг")
    return {
        "status": workerpost.parse_status,   # pending | success | failure
        "task_id": workerpost.task_id,
    }


@router.post("/create_workerpost", status_code=status.HTTP_201_CREATED, summary="Добавить сразу много групп Источников по url")
async def create_workerpost(
        user_id: UserIdDep,
        database: DataBaseDep,
        workerpost_request: WorkerPostRequestAdd,
):
    """Добавляет новый VK аккаунт для парсинга данных"""
    user = await database.user.get_one_or_none(id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )

    try:
        detail = await WorkerPostService(database).create_workerpost(user_id, workerpost_request)
        #detail = await VKGroupSourceService(database).create_groups(user_id, vk_groups_request)
        #detail = await VKAccountBackupService(database).create_accounts(user_id, groups_url)
        return {"status": "OK", "detail": detail}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{workerpost_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить VK Постинг")
async def delete_vk_group(
        user_id: UserIdDep,
        database: DataBaseDep,
        workerpost_id: int,
):
    """Удаляет привязанный VK аккаунт и связанные данные"""
    await database.workerpost.delete(id=workerpost_id, user_id=user_id)
    await database.commit()

    return {"status": "OK"}
