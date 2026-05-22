import random
from typing import Optional

from src.celery_app.revoke_tasks import revoke_celery_task_ids
from src.celery_app.tasks.vk_account_autocurl import connect_vk_account_autocurl
from src.celery_app.tasks import vk_checker_add_account
from src.schemas.vk_account import VKAccountUpdate
from src.services.auth import AuthService
from src.services.live_log import livelogadd


def _target_checker_type(account_type: Optional[str]) -> str:
    t = (account_type or "").strip().lower()
    if t == "backup":
        return "backup"
    if t == "connect":
        return "connect"
    return "checker"


class VKAccountReconnectService:
    def __init__(self, database):
        self.database = database

    async def _resolve_proxy_http(self, account) -> Optional[str]:
        if not account.proxy_id:
            return None
        proxy_db = await self.database.proxy.get_one_or_none(id=account.proxy_id)
        return proxy_db.http if proxy_db else None

    async def _revoke_account_tasks(self, account) -> None:
        celery_tasks_db = await self.database.celery_task.get_all_filtered(
            vk_account_id=account.id,
            user_id=account.user_id,
        )
        task_ids = []
        if account.task_id and account.task_id != "pending":
            task_ids.append(account.task_id)
        task_ids.extend(t.task_id for t in celery_tasks_db if t.task_id)
        revoke_celery_task_ids(task_ids)

    async def _resolve_connect_group_url(self, user_id: int, account_id: int) -> Optional[str]:
        tasks = await self.database.celery_task.get_all_filtered(
            user_id=user_id,
            vk_account_id=account_id,
        )
        for task in reversed(tasks):
            if task.vk_group_url and str(task.vk_group_url).strip():
                return str(task.vk_group_url).strip()
        return None

    async def _default_category_id(self, user_id: int, override: Optional[int]) -> Optional[int]:
        if override is not None:
            return int(override)
        categories = await self.database.category.get_all_filtered(user_id=user_id)
        if not categories:
            return None
        return int(categories[0].id)

    async def reconnect_all_pending(
        self,
        user_id: int,
        category_id: Optional[int] = None,
    ) -> dict:
        accounts = await self.database.vk_account.get_all_filtered(
            user_id=user_id,
            parse_status="pending",
        )
        auth = AuthService()
        proxies = await self.database.proxy.get_all()
        default_category_id = await self._default_category_id(user_id, category_id)

        queued = 0
        queued_autocurl = 0
        queued_checker = 0
        skipped_no_credentials = 0

        for account in accounts:
            if not account.login or not account.encrypted_password:
                skipped_no_credentials += 1
                continue

            password = auth.decrypt_data(account.encrypted_password)
            proxy_http = await self._resolve_proxy_http(account)
            if not proxy_http and proxies:
                proxy = proxies[random.randint(0, len(proxies) - 1)]
                proxy_http = proxy.http

            await self._revoke_account_tasks(account)

            account_type = (account.account_type or "").strip().lower()
            new_task_id = None

            if account_type == "connect":
                vk_group_url = await self._resolve_connect_group_url(user_id, account.id)
                if vk_group_url and default_category_id is not None:
                    task = connect_vk_account_autocurl.delay(
                        user_id,
                        account.id,
                        account.login,
                        password,
                        vk_group_url,
                        default_category_id,
                        proxy_http,
                    )
                    new_task_id = task.id
                    queued_autocurl += 1
                else:
                    target = "connect"
                    task = vk_checker_add_account.delay(
                        user_id,
                        account.id,
                        account.login,
                        password,
                        proxy_http,
                        target,
                    )
                    new_task_id = task.id
                    queued_checker += 1
            else:
                target = _target_checker_type(account.account_type)
                task = vk_checker_add_account.delay(
                    user_id,
                    account.id,
                    account.login,
                    password,
                    proxy_http,
                    target,
                )
                new_task_id = task.id
                queued_checker += 1

            await self.database.vk_account.edit(
                VKAccountUpdate(
                    task_id=new_task_id,
                    parse_status="pending",
                    account_type=_target_checker_type(account.account_type),
                ),
                exclude_unset=True,
                id=account.id,
            )
            queued += 1

        await self.database.commit()

        await livelogadd(
            self.database,
            user_id,
            "account",
            "Массовое переподключение Pending",
            (
                f"total_pending={len(accounts)}; queued={queued}; "
                f"autocurl={queued_autocurl}; checker={queued_checker}; "
                f"skipped_no_credentials={skipped_no_credentials}"
            ),
        )

        return {
            "total_pending": len(accounts),
            "queued": queued,
            "queued_autocurl": queued_autocurl,
            "queued_checker": queued_checker,
            "skipped_no_credentials": skipped_no_credentials,
        }
