from typing import List

from celery import chain
import random

from src.celery_app.tasks import parse_vk_group_sync
from src.celery_app.tasks.db_update_vk_account_group import update_db_group_async
from src.models.celery_task import CeleryTaskOrm
from src.models.vk_account import VKAccountOrm
from src.models.vk_account_cred import VKAccountCredOrm
from src.models.vk_group import VKGroupOrm
from src.schemas.celery_task import CeleryTaskAdd
from src.schemas.vk_account_cred import VKAccountCredAdd
from src.services.auth import AuthService
from src.schemas.vk_account import VKAccountAdd, VKAccountUpdate
from src.celery_app.tasks.vk_api_session import get_vk_account_cred
from src.celery_app.tasks.vk_account_parse import parse_vk_profile_sync
from src.celery_app.tasks.db_update_vk_account import update_db_sync
from src.utils.database_manager import DataBaseManager

class VKAccountLogPass:
    def __init__(self, login: str, password: str):
        self.login = login
        self.password = password

    def __repr__(self):
        return f"VKAccountLogPass(login={self.login!r}, password={self.password!r})"

    @staticmethod
    def parse_creds(vk_creds: str) -> List["VKAccountLogPass"]:
        accounts = []
        for line in vk_creds.strip().splitlines():
            if not line.strip():
                continue  # пропускаем пустые строки
            if ':' not in line:
                continue  # пропускаем некорректные строки
            login, password = line.strip().split(':', 1)
            accounts.append(VKAccountLogPass(login=login, password=password))
        return accounts


class VKAccountBackupService:
    def __init__(self, database: DataBaseManager):
        self.database = database

    async def create_accounts(self, user_id: int, vk_creds: str):
        vk_accounts_log_pass = VKAccountLogPass.parse_creds(vk_creds)

        failed_accounts_log_pass = []
        added_accounts_log_pass = []
        for account_log_pass in vk_accounts_log_pass:
            current_cred = await self.database.vk_account_cred.get_one_or_none(
                login=account_log_pass.login,
            )
            if current_cred:
                failed_accounts_log_pass.append(account_log_pass)
                continue

            encrypted_password = AuthService().encrypt_data(account_log_pass.password)
            vk_account_cred_add = VKAccountCredAdd(
                user_id=user_id,
                login=account_log_pass.login,
                encrypted_password=encrypted_password,
            )
            vk_account_cred = await self.database.vk_account_cred.add(vk_account_cred_add)
            added_accounts_log_pass.append(account_log_pass)

        await self.database.commit()
        print(f"Аккаунты записаны в базу данных: {added_accounts_log_pass}")
        print(f"Аккаунты failed (уже есть в базе): {failed_accounts_log_pass}")

        proxies = await self.database.proxy.get_all()
        index_proxy = random.randint(0, len(proxies)-1)

        for account_log_pass in added_accounts_log_pass:
            proxy = proxies[index_proxy % len(proxies)]
            proxy_http = proxy.http

            index_proxy+=1
            current_cred = await self.database.vk_account_cred.get_one_or_none(
                user_id=user_id,
                login=account_log_pass.login,
            )

            vk_account_add = VKAccountAdd(
                user_id=user_id,
                vk_cred_id=current_cred.id,
                proxy_id=proxy.id,
                vk_account_id=0,
                encrypted_curl="pending",
                vk_account_url="",
                avatar_url="",
                name="pending",
                second_name="pending",
                groups_count=0,
                flood_control=False,
                parse_status="pending",
                task_id="pending",
                account_type="backup",
            )
            vk_account = await self.database.vk_account.add(vk_account_add)
            await self.database.commit()

            task = chain(
                get_vk_account_cred.s(vk_account.id, account_log_pass.login,
                                      AuthService().decrypt_data(current_cred.encrypted_password), proxy_http),
                parse_vk_profile_sync.s(),
                parse_vk_group_sync.s(),
                update_db_sync.s(vk_account.id),
                update_db_group_async.s(vk_account.id, user_id),  # ← data будет первым аргументом
            ).apply_async()

            await self.database.vk_account.edit(
                VKAccountUpdate(task_id=task.id),
                exclude_unset=True,
                id=vk_account.id
            )

            # (опционально) создаем celery_task запись
            celery_task_add = CeleryTaskAdd(
                task_id= task.id,
                type= "add account",
                user_id=user_id,
                vk_account_id=vk_account.id,
                status="starting"
            )
            await self.database.celery_task.add(celery_task_add)

        await self.database.commit()

        detail = {
            "add": added_accounts_log_pass,
            "fail": failed_accounts_log_pass,
        }
        return detail


    async def delete_accounts(self, logins: list[str]):
        creds = await self.database.vk_account_cred.get_all_where(VKAccountCredOrm.login.in_(logins))
        cred_ids = [cred.id for cred in creds]
        vk_accounts = await self.database.vk_account.get_all_where(VKAccountOrm.vk_cred_id.in_(cred_ids))
        vk_account_ids = [vk_account.id for vk_account in vk_accounts]


        await self.database.vk_group.delete_where(VKGroupOrm.vk_admin_main_id.in_(vk_account_ids))
        await self.database.celery_task.delete_where(CeleryTaskOrm.vk_account_id.in_(vk_account_ids))

        # Удаляем связанные аккаунты
        await self.database.vk_account.delete_where(VKAccountOrm.vk_cred_id.in_(cred_ids), VKAccountOrm.account_type=="backup")

        # Удаляем сами креды
        await self.database.vk_account_cred.delete_where(VKAccountCredOrm.login.in_(logins))

        await self.database.commit()
        return logins

    async def get_random_account_backup_curl(self):
        all_vk_accounts_backup = await self.database.vk_account.get_all_filtered(account_type="backup", flood_control=False)

        random_account = random.choice(all_vk_accounts_backup)

        #curl = AuthService().decrypt_data(random_account.encrypted_curl)
        return random_account.id