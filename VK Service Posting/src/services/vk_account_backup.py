import logging
import re
from typing import List
import random

from src.celery_app.tasks import parse_vk_profile_backup_sync
from src.models.celery_task import CeleryTaskOrm
from src.models.vk_account import VKAccountOrm
from src.models.vk_group import VKGroupOrm
from src.schemas.celery_task import CeleryTaskAdd
from src.services.auth import AuthService
from src.schemas.vk_account import VKAccountAdd, VKAccountUpdate
from src.celery_app.tasks.vk_account_backup import get_vk_account_cred
from src.utils.database_manager import DataBaseManager
from src.celery_app.tasks.vk_account_autocurl import connect_vk_account_autocurl

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

    @staticmethod
    def parse_vk_groups(vk_groups_str: str) -> List[str]:
        vk_groups = []
        for line in vk_groups_str.strip().splitlines():
            vk_groups.append(line)
        return vk_groups

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
                token = "",
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
                cookies = "",
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

            proxy_db = await self.database.proxy.get_one_or_none(http=proxy_http)
            await self.database.vk_account.edit(
                VKAccountUpdate(task_id=task.id, proxy_id=proxy_db.id),
                exclude_unset=True,
                id=vk_account_db.id
            )

            # (опционально) создаем celery_task запись
           # celery_task_add = CeleryTaskAdd(
           #     task_id= task.id,
           #     type= "add account",
           #     user_id=user_id,
           #     vk_account_id=vk_account_db.id,
           #     status="starting"
           # )
           # await self.database.celery_task.add(celery_task_add)

        await self.database.commit()

        detail = {
            "add": added_accounts_log_pass,
            "fail": failed_accounts_log_pass,
        }
        return detail


    async def create_account_curl(self, user_id: int, curl: str):
        encrypted_curl = AuthService().encrypt_data(curl)

        # Прокси
        proxies = await self.database.proxy.get_all()

        index_proxy = 0
        if proxies:
            index_proxy = random.randint(0, len(proxies)-1)
            proxy = proxies[index_proxy % len(proxies)]
            proxy_http = proxy.http
        else:
            proxy_http = None
        #=============
        access_token = re.search(r"access_token=([^&]+)", curl).group(1).split("'")[0]
        cookie = re.search(
            r"-b([^&]+)", curl).group(1).split("'")[1]

        new_data = VKAccountAdd(
            user_id=user_id,
            vk_account_id=0,
            token=access_token,
            encrypted_curl=encrypted_curl,
            login="",
            encrypted_password="",
            account_type="backup",
            vk_account_url="",
            avatar_url="",
            name="pending",
            second_name="pending",
            groups_count=0,
            flood_control=False,
            parse_status="pending",
            task_id="pending",
            proxy_id=proxy.id,
            cookies = cookie,
        )
        vk_account = await self.database.vk_account.add(new_data)
        await self.database.commit()

        task = parse_vk_profile_backup_sync.delay(vk_account.id, proxy_http, user_id)

        await self.database.vk_account.edit(VKAccountUpdate(task_id=task.id), exclude_unset=True,
                                            id=vk_account.id)
        await self.database.commit()

        return vk_account

    async def create_vk_accounts_autocurl(self, user_id: int, vk_creds_str: str, vk_groups_str: str, category_id_db: int):
        vk_accounts_log_pass = VKAccountLogPass.parse_creds(vk_creds_str)
        vk_groups = self.parse_vk_groups(vk_groups_str)
        # Прокси
        proxies = await self.database.proxy.get_all()

        for account, group in zip(vk_accounts_log_pass, vk_groups):
            login = account.login
            password = account.password
            encrypted_password = AuthService().encrypt_data(password)
            vk_group_url = group.strip()

            vk_account_db = await self.database.vk_account.get_one_or_none(login=login)
            if vk_account_db:
                logging.info(f"{login} уже есть в базе данных")
                continue

            logging.info(f"{login, password, vk_group_url}")

            index_proxy = 0
            if proxies:
                index_proxy = random.randint(0, len(proxies) - 1)
                proxy = proxies[index_proxy % len(proxies)]
                proxy_http = proxy.http
            else:
                proxy_http = None

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

            task = connect_vk_account_autocurl.delay(user_id, vk_account_db.id, login, password, vk_group_url, category_id_db, proxy_http)

            await self.database.vk_account.edit(VKAccountUpdate(task_id=task.id), exclude_unset=True,
                                                id=vk_account_db.id)

            await self.database.commit()


        return "OK"

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