import random
import re
from typing import List

from celery import chain

from src.celery_app import app  # твой celery app
from src.schemas.celery_task import CeleryTaskAdd, CeleryTaskUpdate
from src.schemas.vk_account import VKAccountAdd, VKAccountUpdate
from src.schemas.vk_account_cred import VKAccountCredAdd
from src.schemas.workerpost import WorkerPostRequestAdd
from src.services.auth import AuthService
from src.services.vk_account_backup import VKAccountLogPass
from src.utils.database_manager import DataBaseManager
from src.celery_app.tasks.workerpost import create_workpost_account

def extract_vk_ids(links: List[str]) -> List[int]:
    """
    Принимает список ссылок на паблики ВК.
    Возвращает список числовых VK ID.
    """
    vk_id_regex = re.compile(r"(?:https?://)?vk\.com/(?:club|public)(\d+)")
    result = []

    for link in links:
        match = vk_id_regex.match(link.strip())
        if match:
            result.append(int(match.group(1)))

    return result

class WorkerPostService:
    def __init__(self, database: DataBaseManager):
        self.database = database

    async def create_workerpost(self, user_id: int, request_add: WorkerPostRequestAdd):
        vk_accounts_log_pass = VKAccountLogPass.parse_creds(request_add.creds)
        vk_groups_ids = extract_vk_ids(request_add.vk_groups_links)

        failed_accounts_log_pass = []
        added_accounts_log_pass = []
        for account_log_pass in vk_accounts_log_pass:
            current_cred = await self.database.vk_account_cred.get_one_or_none(
                login=account_log_pass.login,
            )
            if current_cred:
                added_accounts_log_pass.append(account_log_pass)
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

        main_vk_account_database = await self.database.vk_account.get_one_or_none(account_type="main")
        failed_account_log_pass = []
        failed_group_ids = []

        proxies = await self.database.proxy.get_all()

        for account_log_pass, vk_group_id in zip(added_accounts_log_pass, vk_groups_ids):

            proxy = random.choice(proxies)
            category_database = await self.database.category.get_one_or_none(id=request_add.category_id)

            current_cred = await self.database.vk_account_cred.get_one_or_none(
                user_id=user_id,
                login=account_log_pass.login,
            )

            vk_group_database = await self.database.vk_group.get_one_or_none(vk_group_id=vk_group_id)
            if not vk_group_database:
                print(f"vk group id нет у main account: {vk_group_id}")
                failed_account_log_pass.append(account_log_pass)
                failed_group_ids.append(vk_group_id)
                await self.database.vk_account_cred.delete(id=current_cred.id)
                await self.database.commit()
                continue

            vk_account = await self.database.vk_account.get_one_or_none(vk_cred_id=current_cred.id)
            if not vk_account:
                vk_account_add = VKAccountAdd(
                    user_id=user_id,
                    vk_cred_id=current_cred.id,
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
                    account_type="poster",
                )
                vk_account = await self.database.vk_account.add(vk_account_add)

            task = create_workpost_account.delay(
                account_id_database=vk_account.id,
                main_account_id_database=main_vk_account_database.id,
                vk_group_id_database=vk_group_database.id,
                category_id_database=category_database.id,
                user_id=user_id,
                login=account_log_pass.login,
                password=account_log_pass.password,
                proxy=proxy.http
            )

            await self.database.vk_account.edit(
                VKAccountUpdate(task_id=task.id),
                exclude_unset=True,
                id=vk_account.id
            )

            celery_task = await self.database.celery_task.get_one_or_none(vk_account_id=vk_account.id)
            if not celery_task:
                # (опционально) создаем celery_task запись
                celery_task_add = CeleryTaskAdd(
                    task_id=task.id,
                    type="add workerpost",
                    user_id=user_id,
                    vk_account_id=vk_account.id,
                    clip_list_id=None,
                    status="starting"
                )
                await self.database.celery_task.add(celery_task_add)
            elif celery_task.status == "failed":
                celery_task_update = CeleryTaskUpdate(
                    task_id=task.id,
                    type="add workerpost",
                    vk_account_id=vk_account.id,
                    status="starting"
                )
                await self.database.celery_task.edit(celery_task_update, exclude_unset=True, id=celery_task.id)


        await self.database.commit()

        detail = {
            "add": added_accounts_log_pass,
            "fail": failed_accounts_log_pass,
            "failed group": failed_group_ids,
            "failed account": failed_account_log_pass,
        }
        return detail

    async def get_workpost_all(self, user_id):
        workposts = await self.database.workerpost.get_all_filtered(user_id=user_id)
        workposts_info = []
        for workpost in workposts:
            vk_group = await self.database.vk_group.get_one_or_none(id=workpost.vk_group_id)
            vk_account = await self.database.vk_account.get_one_or_none(id=workpost.vk_account_id)
            category = await self.database.category.get_one_or_none(id=workpost.category_id)
            clip_list = await self.database.clip_list.get_one_or_none(id=category.clip_list_id)
            info = {
                "workpost": workpost,
                "vk_group": vk_group,
                "vk_account": vk_account,
                "category": category,
                "clip_list": clip_list,
            }
            workposts_info.append(info)

        return workposts_info