from fastapi import APIRouter, HTTPException, Response

from src.api.dependencies import UserIdDep, DataBaseDep
from src.schemas.user_auth import UserRequestAdd, UserAdd
from src.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Авторизация и аутентификация"])


@router.post("/login")
async def login_user(
        data: UserRequestAdd,
        database: DataBaseDep,
        response: Response,
):
    user = await database.user.get_one_or_none(email=data.email)
    if not user:
        raise HTTPException(status_code=401, detail="Пользователя не существует.")
    user_hashed_password = await database.user.get_user_with_hashed_password(email=data.email)
    if not AuthService().verify_password(data.password, user_hashed_password.hashed_password):
        raise HTTPException(status_code=401, detail="Пользователя не существует.")

    access_token = AuthService().create_access_token({"user_id": user.id})
    response.set_cookie("access_token", access_token)
    return {"access_token": access_token}


@router.post("/register")
async def register_user(
        data: UserRequestAdd,
        database: DataBaseDep,
):
    hashed_password = AuthService().get_hash_password(data.password)
    new_user_data = UserAdd(email=data.email, hashed_password=hashed_password)
    await database.user.add(new_user_data)
    await database.commit()

    return {"status": "OK"}


@router.get("/only_auth")
async def only_auth_user(
        user_id: UserIdDep,
        database: DataBaseDep,
):
    user = await database.user.get_one_or_none(id=user_id)
    return user


@router.post("/logout")
async def logout(
        response: Response
):
    response.delete_cookie("access_token")
    return {"status": "OK"}
