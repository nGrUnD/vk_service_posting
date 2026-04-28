"""
Повторы vk_login (Selenium) при сбоях прокси и таймаутах UI — общие для autocurl и account checker.
"""
import random
import time
from typing import Any, Optional, Tuple

import requests
from sqlalchemy import select

from src.models.proxy import ProxyOrm
from src.models.vk_account import VKAccountOrm
from src.vk_api_methods.selenium.vk_selenium_captcha import (
    VkLoginFloodControlError,
    normalize_proxy_url,
    vk_login,
)


PROXY_CHECK_URLS = (
    "https://vk.ru/",
    "https://httpbin.org/ip",
)


def is_proxy_connection_error(error: Exception) -> bool:
    error_text = str(error)
    return any(
        marker in error_text
        for marker in [
            "ERR_TUNNEL_CONNECTION_FAILED",
            "Proxy tunnel failed",
            "ERR_PROXY_CONNECTION_FAILED",
            "ERR_NO_SUPPORTED_PROXIES",
            "Page load timeout for https://vk.ru/",
        ]
    )


def is_retryable_selenium_login_error(error: Exception) -> bool:
    error_text = str(error)
    return any(
        marker in error_text
        for marker in [
            "VK password form did not become available",
            "VK login form did not open",
            "VK login input did not become available",
            "element click intercepted",
            "timeout",
            "TimeoutException",
        ]
    )


def is_proxy_online(proxy_http: Optional[str], timeout_sec: float = 6.0) -> bool:
    if not proxy_http:
        return True

    normalized_proxy = normalize_proxy_url(proxy_http)
    proxies = {
        "http": normalized_proxy,
        "https": normalized_proxy,
    }

    for url in PROXY_CHECK_URLS:
        try:
            response = requests.get(url, proxies=proxies, timeout=timeout_sec)
            if response.status_code < 500:
                return True
        except requests.RequestException:
            continue

    return False


def pick_working_proxy(session, user_id: int, current_proxy: Optional[str]):
    stmt_proxies = select(ProxyOrm).where(ProxyOrm.user_id == user_id)
    proxies = session.execute(stmt_proxies).scalars().all()
    candidates = [proxy for proxy in proxies if proxy.http != current_proxy]
    random.shuffle(candidates)

    for proxy in candidates:
        if is_proxy_online(proxy.http):
            return proxy

    return None


def vk_login_with_proxy_retry(
    database_manager,
    vk_account_id: int,
    login: str,
    password: str,
    vk_group_url: Optional[str],
    proxy_http: Optional[str],
    retries: int = 5,
) -> Tuple[Any, Any, Any, Optional[str]]:
    """
    Повторяет vk_login при временных ошибках и переключает прокси при сбое туннеля.
    Возвращает (curl, vk_group_sub, access_token, current_proxy).
    """
    current_proxy = proxy_http

    with database_manager as session:
        stmt = select(VKAccountOrm).where(VKAccountOrm.id == vk_account_id)
        result = session.execute(stmt)
        vk_account_db = result.scalars().one_or_none()
        if vk_account_db is None:
            raise ValueError(f"VK Account {vk_account_id} not found in database")

        for attempt in range(1, retries + 1):
            try:
                if current_proxy and not is_proxy_online(current_proxy):
                    print(
                        f"Попытка {attempt}/{retries}: прокси {current_proxy} не прошёл проверку"
                    )
                    new_proxy = pick_working_proxy(session, vk_account_db.user_id, current_proxy)
                    if not new_proxy:
                        raise RuntimeError(
                            f"Proxy failed and no working proxies available: {current_proxy!s}"
                        )

                    current_proxy = new_proxy.http
                    vk_account_db.proxy_id = new_proxy.id
                    session.commit()
                    print(f"Выбран рабочий прокси: {current_proxy}")

                curl, vk_group_sub, access_token = vk_login(
                    login, password, vk_group_url, current_proxy
                )
                return curl, vk_group_sub, access_token, current_proxy
            except Exception as error:
                if isinstance(error, VkLoginFloodControlError):
                    raise
                if is_proxy_connection_error(error):
                    print(
                        f"Попытка {attempt}/{retries}: сбой прокси {current_proxy}: {error!s}"
                    )
                    new_proxy = pick_working_proxy(session, vk_account_db.user_id, current_proxy)
                    if not new_proxy:
                        raise RuntimeError(
                            f"Proxy failed and no working proxies available: {current_proxy!s}"
                        ) from error

                    current_proxy = new_proxy.http
                    vk_account_db.proxy_id = new_proxy.id
                    session.commit()
                    time.sleep(2)
                    continue

                if is_retryable_selenium_login_error(error) and attempt < retries:
                    print(
                        f"Попытка {attempt}/{retries}: временная ошибка Selenium ({error!s}), "
                        f"повтор"
                    )
                    time.sleep(2)
                    continue

                raise

    raise RuntimeError(
        f"Failed vk_login after {retries} попыток (прокси / таймауты)"
    )
