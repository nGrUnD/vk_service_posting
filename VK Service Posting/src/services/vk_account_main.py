import random

from celery.result import AsyncResult
from celery import chain
from fastapi import HTTPException

from src.celery_app import app as celery_app
from src.celery_app.tasks import parse_vk_group_sync
from src.celery_app.tasks.db_update_vk_account_group import update_db_group_async
from src.models.celery_task import CeleryTaskOrm
from src.models.vk_group import VKGroupOrm
from src.services.auth import AuthService
from src.schemas.vk_account import VKAccountAdd, VKAccountUpdate, VKAccount
from src.celery_app.tasks.vk_api import get_vk_account_curl
from src.celery_app.tasks.vk_account_parse import parse_vk_profile_sync
from src.celery_app.tasks.db_update_vk_account import update_db_sync
from src.services.vk_token_service import TokenService
from src.utils.database_manager import DataBaseManager


class VKAccountMainService:
    def __init__(self, database: DataBaseManager):
        self.database = database

    async def create_account_curl(self, user_id: int, curl: str, account_type: str):
        vk_account = await self.database.vk_account.get_one_or_none(account_type="main")
        if vk_account:
            await self.delete_account(vk_account)

        encrypted_curl = AuthService().encrypt_data(curl)

        new_data = VKAccountAdd(
            user_id=user_id,
            vk_account_id=0,
            encrypted_curl=encrypted_curl,
            account_type=account_type,
            vk_account_url="",
            avatar_url="",
            name="pending",
            second_name="pending",
            groups_count=0,
            flood_control=False,
            parse_status="pending",
            task_id="pending"
        )
        vk_account = await self.database.vk_account.add(new_data)
        await self.database.commit()

        proxies = await self.database.proxy.get_all()

        if proxies:
            index_proxy = random.randint(0, len(proxies)-1)
            proxy = proxies[index_proxy % len(proxies)]
            proxy_http = proxy.http
        else:
            proxy_http = None

        first_task = parse_vk_profile_sync.s(encrypted_curl, vk_account.id)

        # 2. Получи её task_id (еще не отправляя)
        task_id = first_task.freeze().id  # <<< Важно: генерирует task_id, не исполняет

        # task = parse_vk_profile_sync.delay(curl_result=None, account_id=vk_account.id)

        # update task_id
        await self.database.vk_account.edit(VKAccountUpdate(task_id=task_id), exclude_unset=True,
                                            id=vk_account.id)
        await self.database.commit()

        vk_token = TokenService.get_token_from_curl(curl, proxy_http)
        #vk_session = get_vk_session_by_token(vk_token, proxy.http)
        data_task = {
            "token": vk_token,
            "vk_account_id_database": vk_account.id,
            "proxy": proxy_http,
        }
        task_chain = chain(
            parse_vk_profile_sync.s(data_task),
            parse_vk_group_sync.s(),
            update_db_sync.s(vk_account.id),
            update_db_group_async.s(vk_account.id, user_id),  # ← data будет первым аргументом
        )
        task_chain.apply_async(task_id=task_id)
        return vk_account

    async def create_account(self, user_id: int, vk_cred_id: int) -> VKAccount:
        cred = await self.database.vk_account_cred.get_one_or_none(id=vk_cred_id)
        if not cred:
            raise HTTPException(
                status_code=404,
                detail=f"VKAccountCred with id={vk_cred_id} not found"
            )

        new_data = VKAccountAdd(
            user_id=user_id,
            vk_cred_id=vk_cred_id,
            vk_account_id=0,
            encrypted_curl="pending",
            vk_account_url="",
            avatar_url="",
            name="pending",
            second_name="pending",
            groups_count=0,
            flood_control=False,
            parse_status="pending",
            task_id="pending"
        )
        vk_account = await self.database.vk_account.add(new_data)
        await self.database.commit()

        # chain tasks
        task = get_vk_account_curl.delay(vk_account.id, cred.login, AuthService().decrypt_data(cred.encrypted_password))

        # update task_id
        await self.database.vk_account.edit(VKAccountUpdate(task_id=task.id), exclude_unset=True, id=vk_account.id)
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

    async def retry_account(self, user_id: int, vk_account_id: int):
        # 1. Найти аккаунт
        vk_account = await self.database.vk_account.get_one_or_none(id=vk_account_id)
        if not vk_account:
            raise HTTPException(
                status_code=404,
                detail=f"Аккаунт не найден с id {vk_account_id}"
            )

        # 2. Проверить владельца
        if vk_account.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail=f"Доступ запрещён!"
            )

        # 3. Взять зашифрованный curl
        encrypted_curl = vk_account.encrypted_curl

        #await self.create_account_curl(user_id, encrypted_curl, "main")
        #return {"status": "retry_started", "task_id": 0}

        # 4. Сгенерировать новый task_id
        first_task = parse_vk_profile_sync.s(encrypted_curl, vk_account.id)
        new_task_id = first_task.freeze().id

        # 5. Обновить task_id в базе
        await self.database.vk_account.edit(
            VKAccountUpdate(task_id=new_task_id),
            exclude_unset=True,
            id=vk_account.id
        )
        await self.database.commit()

        curl = AuthService().decrypt_data(encrypted_curl)
        vk_token = TokenService.get_token_from_curl(curl, None)

        data_task = {
            "token": vk_token,
            "vk_account_id_database": vk_account.id,
            "proxy": None,
        }

        # 6. Запустить цепочку задач
        task_chain = chain(
            parse_vk_profile_sync.s(data_task),
            parse_vk_group_sync.s(),
            update_db_sync.s(vk_account.id),
            update_db_group_async.s(vk_account.id, user_id),  # ← data будет первым аргументом
        )
        task_chain.apply_async(task_id=new_task_id)

        return {"status": "retry_started", "task_id": new_task_id}

    async def delete_account(self, db_vk_account: VKAccount):

        await self.database.vk_group.delete_where(VKGroupOrm.vk_admin_main_id == db_vk_account.id)
        await self.database.celery_task.delete_where(CeleryTaskOrm.vk_account_id == db_vk_account.id)

        # Удаляем связанные аккаунты
        await self.database.vk_account.delete(id=db_vk_account.id)

        # Удаляем сами креды
        #await self.database.vk_account_cred.delete(id=creds.id)

        await self.database.commit()
        return True

