from typing import Annotated, AsyncGenerator

from fastapi import Depends, Request, HTTPException

from src.database import async_session_maker
from src.services.auth import AuthService
from src.utils.database_manager import DataBaseManager


def get_auth_access_token(request: Request) -> str:
    access_token = request.cookies.get("access_token", None)
    if not access_token:
        raise HTTPException(status_code=401, detail="Вы не предоставили токен доступа")
    return access_token


def get_current_user_id(access_token: str = Depends(get_auth_access_token)) -> int:
    data = AuthService().decode_jwt_token(access_token)
    user_id = data["user_id"]
    return user_id

UserIdDep = Annotated[int, Depends(get_current_user_id)]


def get_database_manager() -> DataBaseManager:
    return DataBaseManager(session_factory=async_session_maker)

async def get_database() -> AsyncGenerator[DataBaseManager, None]:
    async with get_database_manager() as db:
        yield db

DataBaseDep = Annotated[DataBaseManager, Depends(get_database)]