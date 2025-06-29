from fastapi import APIRouter, HTTPException, Body

from src.api.dependencies import DataBaseDep, UserIdDep
from src.schemas.proxy import ProxyRequestAdd, ProxyRequestDelete
from src.schemas.vk_account_cred import VKAccountCredRequestAdd, VKAccountCredAdd
from src.services.auth import AuthService
from src.services.service_proxy import ProxyService

router = APIRouter(prefix="/proxy", tags=["Добавление proxy (http:log:pass@ip:port)"])


@router.get("/{user_id}/get")
async def get_proxy(user_id: UserIdDep, database: DataBaseDep):
    return await database.proxy.get_all_filtered(user_id=user_id)

@router.post("/{user_id}/add")
async def add_proxies(
        user_id : UserIdDep,
        database: DataBaseDep,
        data: ProxyRequestAdd,
):
    proxies = await ProxyService(database, user_id).add_proxies(data.proxys)
    return {"status": "OK", "data": proxies}

@router.delete("/{user_id}/delete")
async def delete_proxy(
    user_id: UserIdDep,
    proxy_id: int,
    database: DataBaseDep,
):
    await database.proxy.delete(id=proxy_id, user_id=user_id)
    await database.commit()

    return {"status": "OK"}

@router.delete("/{user_id}/delete_list")
async def delete_proxy_list(
    user_id: UserIdDep,
    database: DataBaseDep,
    list_proxy: ProxyRequestDelete = Body(...),
):
    await ProxyService(database, user_id).remove_proxies(list_proxy.proxys)

    return {"status": "OK", "deleted_logins": list_proxy}