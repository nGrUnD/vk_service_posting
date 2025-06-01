from fastapi import APIRouter, HTTPException

from src.api.dependencies import DataBaseDep, UserIdDep
from src.schemas.clip_list import ClipListAddRequest, ClipListAdd, ClipListUpdate
from src.services.vk_group_service import VKGroupSourceService

router = APIRouter(prefix="/users/{user_id}/clip_list", tags=["Список клипов"])

@router.post("/add", summary="Добавить список клипов")
async def create(clip_list_request: ClipListAddRequest, database: DataBaseDep, user_id: UserIdDep):
    clip_list_add = ClipListAdd(
        user_id=user_id,
        name=clip_list_request.name,
        parse_status="",
        task_id=""
    )
    new_clip_list = await database.clip_list.add(clip_list_add)
    await database.commit()
    return {"status": "OK", "detail": new_clip_list}

@router.get("/get_all", summary="Получить все списки клипов пользователя")
async def read_all(database: DataBaseDep, user_id: UserIdDep):
    return await database.clip_list.get_all_filtered(user_id=user_id)

@router.get("/get/{clip_list_id}", summary="Получить конкретный список клипов пользователя")
async def read(clip_list_id: int, database: DataBaseDep, user_id: UserIdDep):
    clip_list = await database.clip_list.get_one_or_none(id=clip_list_id)
    if not clip_list:
        raise HTTPException(status_code=404, detail="Список клипов не найден")
    return clip_list

@router.get("/get/{clip_list_id}/tasks_status", summary="Получить списки тасок по списку клипов пользователя")
async def get_all_tasks_status(
    database: DataBaseDep,
    user_id: UserIdDep,
    clip_list_id : int,
):
    clip_list = await database.clip_list.get_one_or_none(id=clip_list_id)
    if not clip_list:
        raise HTTPException(status_code=404, detail="Список клипов не найден")

    detail = await VKGroupSourceService(database).get_tasks_status(user_id, clip_list_id)
    return {"status": "OK", "detail": detail}


@router.put("/edit/{clip_list_id}", summary="Редактировать конкретный список клипов пользователя")
async def update(clip_list_id: int, update_data: ClipListUpdate, database: DataBaseDep, user_id: UserIdDep):
    clip_list = await database.clip_list.get_one_or_none(id=clip_list_id)
    if not clip_list:
        raise HTTPException(status_code=404, detail="Список клипов не найден")
    clip_list_edited = await database.clip_list.edit(update_data, exclude_unset=True, id=clip_list_id)
    await database.commit()
    return {"status": "OK", "detail": clip_list_edited}

@router.delete("/delete/{clip_list_id}", summary="Удалить конкретный список клипов пользователя")
async def delete(clip_list_id: int, database: DataBaseDep, user_id: UserIdDep):
    clip_list = await database.clip_list.get_one_or_none(id=clip_list_id)
    if not clip_list:
        raise HTTPException(status_code=404, detail="Список клипов не найден")
    await database.clip_list.delete(id=clip_list_id)
    await database.commit()
    return {"status": "OK"}
