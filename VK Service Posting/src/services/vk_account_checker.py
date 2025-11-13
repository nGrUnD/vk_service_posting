import asyncio
import random
import string

import aiohttp
import requests

from src.celery_app.tasks import vk_checker_add_account
from src.schemas.vk_account import VKAccountAdd, VKAccountUpdate
from src.services.auth import AuthService
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

    async def change_password(self, data, user_id: int):

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