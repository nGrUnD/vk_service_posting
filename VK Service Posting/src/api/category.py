from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from src.schemas.category import CategoryUpdate, CategoryAddRequest, CategoryAdd

from src.api.dependencies import DataBaseDep, UserIdDep

router = APIRouter(prefix="/users/{user_id}/categories", tags=["Категории"])

@router.post("/add", summary="Добавить категорию")
async def create(category_request: CategoryAddRequest, database: DataBaseDep, user_id: UserIdDep):
    category_add = CategoryAdd(user_id=user_id, **category_request.dict())
    new_category = await database.category.add(category_add)
    await database.commit()
    return {"status": "OK", "detail": new_category}

@router.get("/get_all", summary="Получить все категории пользователя")
async def read_all(database: DataBaseDep, user_id: UserIdDep):
    return await database.category.get_all_filtered(user_id=user_id)

@router.get("/get/{category_id}", summary="Получить конкретную категорию пользователя")
async def read(category_id: int, database: DataBaseDep, user_id: UserIdDep):
    category = await database.category.get_one_or_none(id=category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    return category

@router.put("/edit/{category_id}", summary="Редактировать конкретную категорию пользователя")
async def update(category_id: int, update_data: CategoryUpdate, database: DataBaseDep, user_id: UserIdDep):
    category = await database.category.get_one_or_none(id=category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    category_edited = await database.category.edit(update_data, exclude_unset=True, id=category_id)
    await database.commit()
    return {"status": "OK", "detail": category_edited}

@router.delete("/delete/{category_id}")
async def delete(category_id: int, database: DataBaseDep, user_id: UserIdDep):
    category = await database.category.get_one_or_none(id=category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    await database.category.delete(id=category_id)
    await database.commit()
    return {"status": "OK"}
