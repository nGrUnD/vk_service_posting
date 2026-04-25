import asyncio
import time

import requests
from fastapi import APIRouter, Body

from src.api.dependencies import DataBaseDep, UserIdDep
from src.schemas.proxy import ProxyRequestAdd, ProxyRequestDelete
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
    await ProxyService(database, user_id).delete_proxy_with_reassign(proxy_id)
    return {"status": "OK"}

@router.delete("/{user_id}/delete_list")
async def delete_proxy_list(
    user_id: UserIdDep,
    database: DataBaseDep,
    list_proxy: ProxyRequestDelete = Body(...),
):
    await ProxyService(database, user_id).remove_proxies(list_proxy.proxys)

    return {"status": "OK", "deleted_logins": list_proxy}


def _extract_host_port(proxy_value: str) -> tuple[str, str]:
    value = (proxy_value or "").strip()
    value = value.split("://", 1)[-1]
    value = value.rsplit("@", 1)[-1]
    host_port = value.split("/", 1)[0]
    if ":" in host_port:
        host, port = host_port.rsplit(":", 1)
        return host, port
    return host_port, ""


def _check_single_proxy(proxy_value: str, timeout_sec: float = 4.0) -> dict:
    start = time.perf_counter()
    proxies = {
        "http": proxy_value,
        "https": proxy_value,
    }
    try:
        response = requests.get(
            "https://httpbin.org/ip",
            proxies=proxies,
            timeout=timeout_sec,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        ok = response.status_code == 200
        return {"online": ok, "ping_ms": elapsed_ms if ok else None}
    except Exception:
        return {"online": False, "ping_ms": None}


@router.post("/{user_id}/check_all")
async def check_all_proxies(user_id: UserIdDep, database: DataBaseDep):
    proxies = await database.proxy.get_all_filtered(user_id=user_id)

    async def check_row(proxy_row):
        result = await asyncio.to_thread(_check_single_proxy, proxy_row.http)
        host, port = _extract_host_port(proxy_row.http)
        return {
            "id": proxy_row.id,
            "http": proxy_row.http,
            "ip": host,
            "port": port,
            "geo": "-",
            "status": "online" if result["online"] else "offline",
            "ping_ms": result["ping_ms"],
        }

    items = await asyncio.gather(*(check_row(proxy_row) for proxy_row in proxies))
    return {"items": items}