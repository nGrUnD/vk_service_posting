import asyncio
import random
import string
from functools import partial

import aiohttp
import requests

from src.celery_app.tasks import vk_checker_add_account
from src.schemas.vk_account import VKAccountAdd, VKAccountUpdate
from src.services.auth import AuthService
from src.vk_api_methods.vk_auth import get_new_token_request, get_token
from vk_api.vk_api import vk_api
import logging

from src.schemas.account_checker_batch import AccountCheckerBatchIn
from src.schemas.tools import AccountCheckResult, AccountChangeResult, ChangePasswordByIdItem
from src.services.live_log import livelogadd
from src.utils.database_manager import DataBaseManager
from src.utils.rand_user_agent import get_random_user_agent

def generate_password(length=12):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def _session_cookies_to_header(session: requests.Session) -> str:
    if not session or not getattr(session, "cookies", None) or not session.cookies:
        return ""
    try:
        d = session.cookies.get_dict()
    except Exception:
        return ""
    if not d:
        return ""
    return "; ".join(f"{k}={v}" for k, v in d.items())


class AccountChecker:
    def __init__(self, database: DataBaseManager, concurrency_limit: int = 20):
        self.database = database
        self.concurrency_limit = concurrency_limit

    async def add_account(self, data, user_id: int):
        proxies = await self.database.proxy.get_all()
        if not proxies:
            raise RuntimeError("Нет доступных прокси")

        # Собираем только новые логины (как раньше — дубли пропускаем)
        to_queue: list[tuple[str, str]] = []
        for acc in data.accounts:
            if ":" not in acc:
                continue
            login, password = acc.split(":", 1)
            vk_account_db = await self.database.vk_account.get_one_or_none(login=login)
            if vk_account_db:
                logging.info("%s уже есть в базе данных", login)
                continue
            to_queue.append((login, password))

        if not to_queue:
            return {"detail": "ALL OK", "batch_id": None, "queued": 0}

        label = (getattr(data, "batch_label", None) or "").strip()[:255] or None

        batch_row = await self.database.account_checker_batch.create(
            AccountCheckerBatchIn(
                user_id=user_id,
                total_tasks=len(to_queue),
                completed_tasks=0,
                status="processing",
                label=label,
            )
        )
        await self.database.commit()
        batch_id = batch_row.id

        for i, (login, password) in enumerate(to_queue):
            encrypted_password = AuthService().encrypt_data(password)
            proxy = proxies[i % len(proxies)]
            proxy_http = proxy.http
            logging.info("%s", (login, password, proxy_http))

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
                account_checker_batch_id=batch_id,
            )
            vk_account_db = await self.database.vk_account.add(new_data)
            await self.database.commit()

            task = vk_checker_add_account.delay(
                user_id, vk_account_db.id, login, password, proxy_http, "checker", batch_id
            )

            await self.database.vk_account.edit(
                VKAccountUpdate(task_id=task.id),
                exclude_unset=True,
                id=vk_account_db.id,
            )
            await self.database.commit()

        await livelogadd(
            self.database,
            user_id,
            "account_checker",
            "Проверка аккаунтов: батч создан",
            f"batch_id={batch_id}; queued={len(to_queue)}; label={label or ''}",
        )

        return {"detail": "ALL OK", "batch_id": batch_id, "queued": len(to_queue)}

    @staticmethod
    def _change_password_sync(login: str, old_password: str, proxy_http: str, token: str, cookie: str):
        """
        Блокирующая часть: requests.Session + vk_api.
        Выполняется в пуле потоков через run_in_executor.
        Возвращает (new_password, new_token, cookies_header).
        new_token — новый access_token от VK; cookies — строка из сессии после changePassword
        (для последующих get_new_token_request в воркерах).
        """
        session = requests.Session()
        if proxy_http:
            session.proxies.update({
                'http': proxy_http,
                'https': proxy_http
            })
        else:
            session.trust_env = False
        session.headers.update({
            "User-Agent": get_random_user_agent()
        })

        # 1) Пытаемся обновить токен через web_token
        access_token = get_new_token_request(token, cookie, proxy_http)
        # 2) Если web_token не сработал, используем токен из БД как fallback
        if not access_token:
            access_token = token
        # 3) Если и он не подходит, получаем свежий токен по login/password
        if not access_token:
            fresh = get_token(login, old_password, proxy_http)
            if fresh:
                access_token, _cookies_obj = fresh
        if not access_token:
            raise RuntimeError("Не удалось получить access_token для changePassword")

        vk_session = vk_api.VkApi(token=access_token, session=session)
        vk_session.api_version = "5.251"
        vk_session.app_id = 6287487

        new_password = generate_password()
        vk = vk_session.get_api()
        resp = vk.account.changePassword(old_password=old_password, new_password=new_password)
        # API может не вернуть token, тогда сохраняем текущий рабочий.
        new_token = resp.get("token") or access_token
        http_sess = getattr(vk_session, "http", None) or session
        new_cookie_header = _session_cookies_to_header(http_sess) or _session_cookies_to_header(session)
        return new_password, new_token, new_cookie_header

    async def _change_password_one(
        self,
        login: str,
        old_password: str,
        user_id: int,
        semaphore: asyncio.Semaphore,
    ):
        """
        Одна асинхронная задача смены пароля для одного аккаунта.
        Возвращает AccountChangeResult.
        """
        try:
            # 1) получить запись аккаунта + прокси в отдельной сессии,
            # чтобы параллельные задачи не делили один AsyncSession.
            async with DataBaseManager(self.database.session_factory) as db:
                vk_account_db = await db.vk_account.get_one_or_none(login=login)
                if not vk_account_db:
                    return AccountChangeResult(login=login, password=old_password + "\tNot found account")

                proxy_db = await db.proxy.get_one_or_none(id=vk_account_db.proxy_id)
                proxy_http = proxy_db.http if proxy_db else None

            # 3) выполнить блокирующую часть в пуле потоков
            async with semaphore:
                loop = asyncio.get_running_loop()
                new_password, new_token, new_cookies = await loop.run_in_executor(
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

            # 4) сохранить изменения в БД (асинхронно, отдельная сессия)
            encrypted_password = AuthService().encrypt_data(new_password)
            async with DataBaseManager(self.database.session_factory) as db:
                if new_cookies:
                    await db.vk_account.edit(
                        VKAccountUpdate(
                            encrypted_password=encrypted_password,
                            token=new_token,
                            cookies=new_cookies,
                        ),
                        exclude_unset=True,
                        id=vk_account_db.id
                    )
                else:
                    await db.vk_account.edit(
                        VKAccountUpdate(encrypted_password=encrypted_password, token=new_token),
                        exclude_unset=True,
                        id=vk_account_db.id
                    )
                await db.commit()

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

    async def change_passwords_by_ids(self, vk_account_ids: list[int], user_id: int) -> list[ChangePasswordByIdItem]:
        semaphore = asyncio.Semaphore(self.concurrency_limit)
        ordered: list[int] = []
        seen: set[int] = set()
        for aid in vk_account_ids:
            if aid not in seen:
                seen.add(aid)
                ordered.append(aid)
        tasks = [self._change_password_one_by_account_id(aid, user_id, semaphore) for aid in ordered]
        return list(await asyncio.gather(*tasks))

    async def _change_password_one_by_account_id(
        self,
        account_id: int,
        user_id: int,
        semaphore: asyncio.Semaphore,
    ) -> ChangePasswordByIdItem:
        try:
            async with DataBaseManager(self.database.session_factory) as db:
                acc = await db.vk_account.get_one_or_none(id=account_id, user_id=user_id)
                if not acc:
                    return ChangePasswordByIdItem(
                        vk_account_id=account_id, ok=False, login=None, detail="Аккаунт не найден",
                    )
                if not acc.login:
                    return ChangePasswordByIdItem(
                        vk_account_id=account_id, ok=False, login=None, detail="Нет логина",
                    )
                if not acc.encrypted_password:
                    return ChangePasswordByIdItem(
                        vk_account_id=account_id, ok=False, login=acc.login, detail="Нет пароля в БД",
                    )
                if acc.parse_status != "success":
                    return ChangePasswordByIdItem(
                        vk_account_id=account_id,
                        ok=False,
                        login=acc.login,
                        detail=f"Нужен parse_status=success, сейчас: {acc.parse_status}",
                    )
                proxy_http = None
                if acc.proxy_id:
                    proxy_db = await db.proxy.get_one_or_none(id=acc.proxy_id)
                    proxy_http = proxy_db.http if proxy_db else None
                login = acc.login
                old_password = AuthService().decrypt_data(acc.encrypted_password)
                token = acc.token or ""
                cookies = acc.cookies or ""
                row_id = acc.id

            async with semaphore:
                loop = asyncio.get_running_loop()
                new_password, new_token, new_cookies = await loop.run_in_executor(
                    None,
                    partial(
                        self._change_password_sync,
                        login,
                        old_password,
                        proxy_http,
                        token,
                        cookies,
                    ),
                )

            encrypted_password = AuthService().encrypt_data(new_password)
            async with DataBaseManager(self.database.session_factory) as db:
                if new_cookies:
                    await db.vk_account.edit(
                        VKAccountUpdate(
                            encrypted_password=encrypted_password,
                            token=new_token,
                            cookies=new_cookies,
                        ),
                        exclude_unset=True,
                        id=row_id,
                    )
                else:
                    await db.vk_account.edit(
                        VKAccountUpdate(encrypted_password=encrypted_password, token=new_token),
                        exclude_unset=True,
                        id=row_id,
                    )
                await db.commit()

            return ChangePasswordByIdItem(vk_account_id=account_id, ok=True, login=login, detail=None)
        except Exception as e:
            logging.exception("change_passwords_by_ids account_id=%s", account_id)
            return ChangePasswordByIdItem(vk_account_id=account_id, ok=False, login=None, detail=str(e))