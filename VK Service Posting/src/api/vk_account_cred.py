from fastapi import APIRouter, HTTPException, Body

from src.api.dependencies import DataBaseDep, UserIdDep
from src.schemas.vk_account_cred import VKAccountCredRequestAdd, VKAccountCredAdd
from src.services.auth import AuthService

router = APIRouter(prefix="/vk_account_cred", tags=["Добавление cred (log:pass) от VK Аккаунта"])


@router.get("/{user_id}/vk_account_creds")
async def get_vk_account_creds(user_id: UserIdDep, database: DataBaseDep):
    return await database.vk_account_cred.get_all_filtered(user_id=user_id)


@router.get("/{user_id}/vk_account_creds/{vk_account_cred_id}")
async def get_vk_account_cred(user_id: UserIdDep, vk_account_cred_id: int, database: DataBaseDep):
    return await database.vk_account_cred.get_one_or_none(id=vk_account_cred_id, user_id=user_id)


@router.post("/{user_id}/vk_account_creds")
async def add_vk_account_cred(
        user_id : UserIdDep,
        database: DataBaseDep,
        data: VKAccountCredRequestAdd = Body(),
):
    # Check for existing cred (None means “not found”)
    current_cred = await database.vk_account_cred.get_one_or_none(
        user_id=user_id,
        login=data.login,
    )
    if current_cred is not None:
        # We found an existing credential → conflict
        raise HTTPException(
            status_code=400,
            detail="Аккаунт с таким логином уже существует"
        )

    # No existing cred → proceed to hash & insert
    encrypted_password = AuthService().encrypt_data(data.password)
    dto = VKAccountCredAdd(
        user_id=user_id,
        login=data.login,
        encrypted_password=encrypted_password,
    )
    cred = await database.vk_account_cred.add(dto)
    await database.commit()

    return {"status": "OK", "data": cred}

@router.delete("/{user_id}/vk_account_creds/{vk_account_cred_id}")
async def delete_vk_account_cred(
    user_id: UserIdDep,
    vk_account_cred_id: int,
    database: DataBaseDep,
):
    await database.vk_account_cred.delete(id=vk_account_cred_id, user_id=user_id)
    await database.commit()

    return {"status": "OK"}