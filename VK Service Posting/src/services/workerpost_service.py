import logging
import random
import re
from typing import List

from src.schemas.celery_task import CeleryTaskAdd, CeleryTaskUpdate
from src.schemas.vk_account import VKAccountUpdate
from src.schemas.workerpost import WorkerPostRequestAdd
from src.services.auth import AuthService
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
        #vk_accounts_log_pass = VKAccountLogPass.parse_creds(request_add.creds)

        vk_groups_ids = extract_vk_ids(request_add.vk_groups_links)

        main_vk_account_database = await self.database.vk_account.get_one_or_none(account_type="main", user_id=user_id)
        failed_account_log_pass = []
        failed_group_ids = []

        vk_accounts_backup_free = await self.database.vk_account.get_all_filtered(account_type="backup", parse_status="success", flood_control=False)

        for vk_account_backup_db, vk_group_id in zip(vk_accounts_backup_free, vk_groups_ids):
            category_database = await self.database.category.get_one_or_none(id=request_add.category_id)


            vk_group_database = await self.database.vk_group.get_one_or_none(vk_group_id=vk_group_id)
            if not vk_group_database:
                print(f"vk group id нет у main account: {vk_group_id}")
                failed_group_ids.append(vk_group_id)
                #await self.database.vk_account_cred.delete(id=current_cred.id)
                #await self.database.commit()
                continue

            await self.database.vk_account.edit(
                VKAccountUpdate(account_type="posting"),
                exclude_unset=True,
                id=vk_account_backup_db.id
            )

            await self.database.commit()


            password = AuthService().decrypt_data(vk_account_backup_db.encrypted_password)
            token_db = vk_account_backup_db.token

            proxy_db = await self.database.proxy.get_one_or_none(id=vk_account_backup_db.proxy_id)
            proxy_http = None
            if proxy_db:
                proxy_http = proxy_db.http

            logging.info(f'workerpost_service proxy_http: {proxy_http}')

            task = create_workpost_account.delay(
                account_id_database=vk_account_backup_db.id,
                main_account_id_database=main_vk_account_database.id,
                vk_group_id_database=vk_group_database.id,
                category_id_database=category_database.id,
                user_id=user_id,
                login=vk_account_backup_db.login,
                password=password,
                token_db=token_db,
                proxy=proxy_http
            )

            await self.database.vk_account.edit(
                VKAccountUpdate(task_id=task.id),
                exclude_unset=True,
                id=vk_account_backup_db.id
            )

            celery_task = await self.database.celery_task.get_one_or_none(vk_account_id=vk_account_backup_db.id, type="add workerpost")
            if not celery_task:
                # (опционально) создаем celery_task запись
                celery_task_add = CeleryTaskAdd(
                    task_id=task.id,
                    type="add workerpost",
                    user_id=user_id,
                    vk_account_id=vk_account_backup_db.id,
                    clip_list_id=None,
                    status="starting"
                )
                await self.database.celery_task.add(celery_task_add)
            elif celery_task.status == "failed":
                celery_task_update = CeleryTaskUpdate(
                    task_id=task.id,
                    type="add workerpost",
                    vk_account_id=vk_account_backup_db.id,
                    status="starting"
                )
                await self.database.celery_task.edit(celery_task_update, exclude_unset=True, id=celery_task.id)

            await self.database.commit()


        await self.database.commit()

        detail = {
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
            #clip_list = await self.database.clip_list.get_one_or_none(id=category.clip_list_id)
            info = {
                "workpost": workpost,
                "vk_group": vk_group,
                "vk_account": vk_account,
                "category": category,
                #"clip_list": clip_list,
            }
            workposts_info.append(info)

        return workposts_info

    async def revert_account_backup(self, account_id_db):
        await self.database.vk_account.edit(
            VKAccountUpdate(account_type="backup"),
            exclude_unset=True,
            id=account_id_db
        )
        await self.database.commit()
