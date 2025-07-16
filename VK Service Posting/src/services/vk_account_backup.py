from typing import List
import random

from src.models.celery_task import CeleryTaskOrm
from src.models.vk_account import VKAccountOrm
from src.models.vk_group import VKGroupOrm
from src.schemas.celery_task import CeleryTaskAdd
from src.services.auth import AuthService
from src.schemas.vk_account import VKAccountAdd, VKAccountUpdate
from src.celery_app.tasks.vk_account_backup import get_vk_account_cred
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
            vk_account_db = await self.database.vk_account.get_one_or_none(
                login=account_log_pass.login,
            )
            if vk_account_db:
                failed_accounts_log_pass.append(account_log_pass)
                continue

            encrypted_password = AuthService().encrypt_data(account_log_pass.password)
            new_vk_account_data = VKAccountAdd(
                user_id = user_id,
                proxy_id = None,
                vk_account_id = 0,
                encrypted_curl = "",
                login = account_log_pass.login,
                encrypted_password = encrypted_password,
                vk_account_url = "pending",
                avatar_url = "pending",
                name = "pending",
                second_name = "pending",
                groups_count = 0,
                flood_control = False,
                parse_status = "pending",
                task_id = "0",
                account_type = "backup",
            )
            await self.database.vk_account.add(new_vk_account_data)
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
            vk_account_db = await self.database.vk_account.get_one_or_none(
                user_id=user_id,
                login=account_log_pass.login,
            )

            password = AuthService().decrypt_data(vk_account_db.encrypted_password)

            task = get_vk_account_cred.delay(vk_account_db.id, account_log_pass.login, password, proxy_http)

            await self.database.vk_account.edit(
                VKAccountUpdate(task_id=task.id),
                exclude_unset=True,
                id=vk_account_db.id
            )

            # (опционально) создаем celery_task запись
            celery_task_add = CeleryTaskAdd(
                task_id= task.id,
                type= "add account",
                user_id=user_id,
                vk_account_id=vk_account_db.id,
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
        vk_accounts = await self.database.vk_account.get_all_where(VKAccountOrm.login.in_(logins))
        vk_account_ids = [vk_account.id for vk_account in vk_accounts]


        await self.database.vk_group.delete_where(VKGroupOrm.vk_admin_main_id.in_(vk_account_ids))
        await self.database.celery_task.delete_where(CeleryTaskOrm.vk_account_id.in_(vk_account_ids))

        # Удаляем связанные аккаунты
        await self.database.vk_account.delete_where(VKAccountOrm.login.in_(logins))

        await self.database.commit()
        return logins

    async def get_random_account_backup_curl(self):
        all_vk_accounts_backup = await self.database.vk_account.get_all_filtered(account_type="backup", parse_status="success", flood_control=False)

        random_account = random.choice(all_vk_accounts_backup)

        #curl = AuthService().decrypt_data(random_account.encrypted_curl)
        return random_account.id