import asyncio
import random
import string
from functools import partial

import aiohttp
import requests

from src.celery_app.tasks import vk_checker_add_account
from src.schemas.vk_account import VKAccountAdd, VKAccountUpdate
from src.services.auth import AuthService
from src.vk_api_methods.vk_auth import get_new_token_request
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

    async def add_account(self, data, user_id: int):
        proxies = await self.database.proxy.get_all()
        if not proxies:
            raise RuntimeError("Нет доступных прокси")

        for i, acc in enumerate(data.accounts):
            if ":" not in acc:
                continue
            login, password = acc.split(":", 1)
            encrypted_password = AuthService().encrypt_data(password)
            proxy = proxies[i % len(proxies)]
            proxy_http = proxy.http

            vk_account_db = await self.database.vk_account.get_one_or_none(login=login)
            if vk_account_db:
                logging.info(f"{login} уже есть в базе данных")
                continue

            logging.info(f"{login, password, proxy_http}")

            new_data = VKAccountAdd(
                user_id=user_id,
                vk_account_id=0,
                token="",
                encrypted_curl="",
                login=login,
                encrypted_password=encrypted_password,
                account_type="connect",
                vk_account_url="",
                avatar_url="",
                name="pending",
                second_name="pending",
                groups_count=0,
                flood_control=False,
                parse_status="pending",
                task_id="pending",
                proxy_id=proxy.id,
                cookies="",
            )
            vk_account_db = await self.database.vk_account.add(new_data)
            await self.database.commit()

            task = vk_checker_add_account.delay(user_id, vk_account_db.id, login, password, proxy_http)

            await self.database.vk_account.edit(VKAccountUpdate(task_id=task.id), exclude_unset=True,
                                                id=vk_account_db.id)

            await self.database.commit()

    @staticmethod
    def _change_password_sync(login: str, old_password: str, proxy_http: str, token: str, cookie: str):
        """
        Блокирующая часть: requests.Session + vk_api.
        Выполняется в пуле потоков через run_in_executor.
        Возвращает (new_password, new_token). Может кидать исключение.
        """
        session = requests.Session()
        session.proxies.update({
            'http': proxy_http,
            'https': proxy_http
        })
        session.headers.update({
            "User-Agent": get_random_user_agent()
        })

        access_token = get_new_token_request(token, cookie, proxy_http)

        vk_session = vk_api.VkApi(token=access_token, session=session)
        vk_session.api_version = "5.251"
        vk_session.app_id = 6287487

        new_password = generate_password()
        vk = vk_session.get_api()
        resp = vk.account.changePassword(old_password=old_password, new_password=new_password)
        new_token = resp.get("token")
        return new_password, new_token

    async def _change_password_one(self, login: str, old_password: str, user_id: int, semaphore: asyncio.Semaphore):
        """
        Одна асинхронная задача смены пароля для одного аккаунта.
        Возвращает AccountChangeResult.
        """
        try:
            # 1) получить запись аккаунта
            vk_account_db = await self.database.vk_account.get_one_or_none(login=login)
            if not vk_account_db:
                return AccountChangeResult(login=login, password=old_password + "\tNot found account")

            # 2) прокси
            proxy_db = await self.database.proxy.get_one_or_none(id=vk_account_db.proxy_id)
            proxy_http = proxy_db.http if proxy_db else None

            # 3) выполнить блокирующую часть в пуле потоков
            async with semaphore:
                loop = asyncio.get_running_loop()
                new_password, new_token = await loop.run_in_executor(
                    None,
                    partial(
                        self._change_password_sync,
                        login,
                        old_password,
                        proxy_http,
                        vk_account_db.token,
                        vk_account_db.cookies
                    )
                )

            # 4) сохранить изменения в БД (асинхронно)
            encrypted_password = AuthService().encrypt_data(new_password)
            await self.database.vk_account.edit(
                VKAccountUpdate(encrypted_password=encrypted_password, token=new_token),
                exclude_unset=True,
                id=vk_account_db.id
            )
            await self.database.commit()

            logging.info(f"Login: {login} NewPassword: {new_password}")
            return AccountChangeResult(login=login, password=new_password)

        except Exception as e:
            logging.exception(f"Ошибка при смене пароля для {login}: {e}")
            return AccountChangeResult(login=login, password=old_password + f"\t{e}")

    async def change_password(self, data, user_id: int):
        """
        Параллельно меняем пароли со стабильным ограничением concurrency.
        """
        # подготовка задач
        semaphore = asyncio.Semaphore(self.concurrency_limit)
        tasks = []

        for acc in data.accounts:
            if ":" not in acc:
                continue
            login, password = acc.split(":", 1)
            tasks.append(self._change_password_one(login, password, user_id, semaphore))

        # запуск параллельно
        results = await asyncio.gather(*tasks)
        return results