"""
Повторы vk_login (Selenium) при сбоях прокси и таймаутах UI — общие для autocurl и account checker.
"""
import random
import time
from typing import Any, Optional, Tuple

from sqlalchemy import select

from src.models.proxy import ProxyOrm
from src.models.vk_account import VKAccountOrm
from src.vk_api_methods.selenium.vk_selenium_captcha import VkLoginFloodControlError, vk_login


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
            "timeout",
            "TimeoutException",
        ]
    )


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
                    stmt_proxies = select(ProxyOrm).where(ProxyOrm.http != current_proxy)
                    proxies = session.execute(stmt_proxies).scalars().all()

                    if not proxies:
                        raise RuntimeError(
                            f"Proxy failed and no other proxies available: {current_proxy!s}"
                        ) from error

                    new_proxy = random.choice(proxies)
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
