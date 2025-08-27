import random
import re
from typing import List

from src.celery_app import app  # твой celery app
from src.schemas.vk_group import VKGroupRequestAddUrl, VKGroupAdd
from src.services.auth import AuthService
from src.services.celery_task import CeleryTaskService
from src.services.vk_account_backup import VKAccountBackupService
from src.utils.database_manager import DataBaseManager

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

class VKGroupSourceService:
    def __init__(self, database: DataBaseManager):
        self.database = database

    async def create_groups(self, user_id: int, vk_group_urls_request: VKGroupRequestAddUrl):
        global vk_link
        vk_groups_ids = extract_vk_ids(vk_group_urls_request.vk_links)
        print(vk_groups_ids)

        print(vk_group_urls_request)

        task_ids = []
        vk_link_map = dict(zip(vk_groups_ids, vk_group_urls_request.vk_links))

        proxies = await self.database.proxy.get_all()
        index_proxy = random.randint(0, len(proxies)-1)

        for vk_group_id in vk_groups_ids:
            proxy = proxies[index_proxy % len(proxies)]
            index_proxy+=1

            vk_link = vk_link_map[vk_group_id]
            vk_group_database = await self.database.vk_group.get_one_or_none(vk_group_id=vk_group_id)
            if not vk_group_database:
                group_new = VKGroupAdd(
                    user_id=user_id,
                    vk_group_id=vk_group_id,
                    vk_group_type="source",
                    vk_group_url=vk_link,
                    avatar_url="none",
                    name="",
                    clips_count=0,
                    parse_status="starting",
                    task_id=""
                )
                vk_group_database = await self.database.vk_group.add(group_new)


            vk_group_database_id = vk_group_database.id
            vk_account_id = await VKAccountBackupService(self.database).get_random_account_backup_curl()

            vk_account_db = await self.database.vk_account.get_one_or_none(id=vk_account_id)

            login = vk_account_db.login
            password = AuthService().decrypt_data(vk_account_db.encrypted_password) # current_cred.encrypted_password
            token_db = vk_account_db.token
            print(login)
            print(password)
            print(token_db)

            task = app.send_task(
                'src.tasks.parse_vk_group_clips_sync',  # имя таски, как зарегистрирована
                args=[vk_group_id, login, password, token_db, vk_account_db.id, proxy.http, user_id, vk_group_urls_request.clip_list_id, vk_group_database_id, vk_group_urls_request.min_views, vk_group_urls_request.date_range]
            )
            task_ids.append(task.id)
            await (CeleryTaskService(self.database).
                   create_celery_task_record(task.id, user_id, "parse source group",
                                             vk_account_id, vk_group_urls_request.clip_list_id,
                                             vk_link))

        await self.database.commit()
        return {"started_tasks": len(task_ids), "task_ids": task_ids}

    async def get_tasks_status(self, user_id: int, clip_list_id):
        celery_tasks = await self.database.celery_task.get_all_filtered(clip_list_id=clip_list_id, user_id=user_id)

        tasks_success = []
        tasks_failed = []
        tasks_in_progress = []
        tasks_empty = []

        for task in celery_tasks:
            status = (task.status or "").lower()
            if status == "success":
                tasks_success.append(task)
            elif status == "failure":
                tasks_failed.append(task)
            elif status in ("started", "pending", "in_progress"):
                tasks_in_progress.append(task)
            elif status == "empty":
                tasks_empty.append(task)
            else:
                # Если есть другие статусы — можно сюда добавить или игнорировать
                pass

        return {
            "tasks_success": tasks_success,
            "tasks_failed": tasks_failed,
            "tasks_in_progress": tasks_in_progress,
            "tasks_empty": tasks_empty,
            "all_tasks": celery_tasks,
        }

