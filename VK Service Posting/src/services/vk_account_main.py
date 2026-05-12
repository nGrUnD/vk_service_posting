import re

from celery.result import AsyncResult
from celery import chain
from fastapi import HTTPException
from sqlalchemy import update, or_

from src.celery_app import app as celery_app
from src.celery_app.revoke_tasks import revoke_celery_task_ids
from src.celery_app.tasks import parse_vk_group_sync, vk_account_main_update_groups
from src.celery_app.tasks.db_update_vk_account_group import update_db_group_async
from src.models.celery_task import CeleryTaskOrm
from src.models.vk_group import VKGroupOrm
from src.services.auth import AuthService
from src.schemas.vk_account import VKAccountAdd, VKAccountUpdate, VKAccount
from src.celery_app.tasks.vk_api import get_vk_account_curl
from src.celery_app.tasks.vk_account_parse import parse_vk_profile_main_sync
from src.celery_app.tasks.db_update_vk_account import update_db_sync
from src.services.vk_token_service import TokenService
from src.utils.database_manager import DataBaseManager
from src.services.live_log import livelogadd


class VKAccountMainService:
    def __init__(self, database: DataBaseManager):
        self.database = database

    @staticmethod
    def _extract_token_and_cookies_from_curl(curl: str) -> tuple[str | None, str | None]:
        parsed_request = TokenService.parse_curl(curl)
        if not parsed_request:
            return None, None

        raw_token = parsed_request.data.get("access_token")
        cookie_string = None
        if parsed_request.cookies:
            cookie_string = "; ".join(f"{key}={value}" for key, value in parsed_request.cookies.items())

        return raw_token, cookie_string

    async def create_account_curl(self, user_id: int, curl: str, account_type: str):
        old_main_account = await self.database.vk_account.get_one_or_none(account_type="main")

        encrypted_curl = AuthService().encrypt_data(curl)
        raw_token, cookie_string = self._extract_token_and_cookies_from_curl(curl)
        proxy_http = None

        try:
            vk_token = TokenService.get_token_from_curl_direct(curl)
        except Exception as error:
            raise ValueError(
                "Main account direct authorization is no longer valid. "
                "Reconnect the main account with a fresh add main curl."
            ) from error

        if vk_token:
            raw_token = vk_token

        new_data = VKAccountAdd(
            user_id=user_id,
            vk_account_id=0,
            token=raw_token or "curl",
            encrypted_curl=encrypted_curl,
            login="",
            encrypted_password="",
            account_type=account_type,
            vk_account_url="",
            avatar_url="",
            name="pending",
            second_name="pending",
            groups_count=0,
            flood_control=False,
            parse_status="pending",
            task_id="pending",
            cookies = cookie_string,
        )
        vk_account = await self.database.vk_account.add(new_data)
        await self.database.commit()

        # Main account is shared for all user's publics:
        # always point user's groups to the newly added main account.
        await self.database.session.execute(
            update(VKGroupOrm)
            .where(
                VKGroupOrm.user_id == user_id,
                or_(
                    VKGroupOrm.vk_admin_main_id == old_main_account.id if old_main_account else False,
                    VKGroupOrm.vk_admin_main_id.is_(None),
                ),
            )
            .values(vk_admin_main_id=vk_account.id)
        )
        await self.database.commit()

        if old_main_account:
            await self.delete_account(old_main_account)

        #vk_session = get_vk_session_by_token(vk_token, proxy.http)

        task = parse_vk_profile_main_sync.delay(vk_token, vk_account.id, proxy_http, user_id)

        await self.database.vk_account.edit(
            VKAccountUpdate(
                task_id=task.id,
                token=raw_token,
                cookies=cookie_string,
            ),
            exclude_unset=True,
            id=vk_account.id
        )

        await livelogadd(self.database, user_id, "account", "Аккаунт Main создан", f"account_id={vk_account.id}")

        await self.database.commit()


        return vk_account


    async def get_status(self, account_id: int) -> dict:
        account = await self.database.vk_account.get_one_or_none(id=account_id)
        if not account:
            raise ValueError("Account not found")
        res1 = AsyncResult(account.task_id, app=celery_app)
        parent_id = getattr(res1, 'parent_id', None)
        res2 = AsyncResult(parent_id, app=celery_app) if parent_id else None
        return {
            'first': {'id': res1.id, 'status': res1.status},
            'second': {'id': res2.id if res2 else None, 'status': res2.status if res2 else None}
        }

    async def retry_account(self, user_id: int):
        vk_account = await self.database.vk_account.get_one_or_none(account_type="main")
        if not vk_account:
            raise HTTPException(
                status_code=404,
                detail=f"Аккаунт не найден main"
            )

        if vk_account.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail=f"Доступ запрещён!"
            )

        encrypted_curl = vk_account.encrypted_curl
        curl = AuthService().decrypt_data(encrypted_curl)

        access_token = re.search(r"access_token=([^&]+)", curl).group(1).split("'")[0]
        cookie = re.search(
            r"-b([^&]+)", curl).group(1).split("'")[1]

        account_id = vk_account.vk_account_id

        task = vk_account_main_update_groups.delay(user_id, vk_account.id, account_id, cookie, access_token, None)
        new_task_id = task.id

        # 5. Обновить task_id в базе
        await self.database.vk_account.edit(
            VKAccountUpdate(task_id=new_task_id),
            exclude_unset=True,
            id=vk_account.id
        )
        await self.database.commit()

        await livelogadd(
            self.database,
            user_id,
            "account",
            "Обновление групп Main перезапущено",
            f"account_id={vk_account.id}; task_id={new_task_id}",
        )

        return {"status": "retry_started", "task_id": new_task_id}

    async def delete_account(self, db_vk_account: VKAccount):
        await self.database.session.execute(
            update(VKGroupOrm)
            .where(VKGroupOrm.vk_admin_main_id == db_vk_account.id)
            .values(vk_admin_main_id=None)
        )
        celery_rows = await self.database.celery_task.get_all_filtered(vk_account_id=db_vk_account.id)
        revoke_celery_task_ids([db_vk_account.task_id, *(t.task_id for t in celery_rows)])
        await self.database.celery_task.delete_where(CeleryTaskOrm.vk_account_id == db_vk_account.id)

        # Удаляем связанные аккаунты
        await self.database.vk_account.delete(id=db_vk_account.id)

        # Удаляем сами креды
        #await self.database.vk_account_cred.delete(id=creds.id)

        await self.database.commit()
        return True

