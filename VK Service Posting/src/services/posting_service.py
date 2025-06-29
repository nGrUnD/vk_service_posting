import random
from typing import List, Optional

from src.celery_app.tasks import create_post

from src.repositories.category import CategoryRepository
from src.repositories.clip_list import ClipListRepository
from src.repositories.proxy import ProxyRepository
from src.repositories.schedule_posting import SchedulePostingRepository
from src.repositories.vk_account import VKAccountRepository
from src.repositories.vk_clip import VKClipRepository
from src.repositories.workerpost import WorkerPostRepository
from src.schemas.schedule_posting import SchedulePostingAdd, SchedulePostingUpdate
from src.schemas.vk_clip import VKClipOut
from src.services.auth import AuthService
from src.services.vk_token_service import TokenService


class PostingService:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        self.workpost_repo = WorkerPostRepository(self.session)
        self.category_repo = CategoryRepository(self.session)
        self.schedule_posting = SchedulePostingRepository(self.session)
        self.clip_list = ClipListRepository(self.session)
        self.vk_clip = VKClipRepository(self.session)
        self.vk_account_repo = VKAccountRepository(self.session)
        self.proxy = ProxyRepository(self.session)

        return self

    async def __aexit__(self, *args):
        await self.session.rollback()
        await self.session.close()

    async def commit(self):
        await self.session.commit()

    def get_random_clip(self, clips: List[VKClipOut]) -> Optional[VKClipOut]:
        if not clips:
            return None
        return random.choice(clips)

    async def check_and_schedule(self, minute: int):
        #print(minute)
        workposts = await self.workpost_repo.get_all()
        proxies = await self.proxy.get_all()
        index_proxy = random.randint(0, len(proxies))

        for workpost in workposts:
            proxy = proxies[index_proxy % len(proxies)]
            index_proxy+=1
            #print(workpost)
            category = await self.category_repo.get_one_or_none(id=workpost.category_id)
            #print(category)
            if not category.is_active:
                continue

            hourly_limit = category.hourly_limit
            #print(f"hourly_limit: {hourly_limit}")
            minute_post = int(60 / hourly_limit)

            is_can_post = minute % minute_post == 0
            if not is_can_post:
                continue

            #print("post")
            clip_list = await self.clip_list.get_one_or_none(id=category.clip_list_id)
            vk_account = await self.vk_account_repo.get_one_or_none(id=workpost.vk_account_id)

            clips = await self.vk_clip.get_all_filtered(clip_list_id=clip_list.id)

            random_clip = self.get_random_clip(clips)
            if not random_clip:
                print("Не удалось получить случайный клип")
                continue

            clip_data = random_clip.model_dump() if random_clip else None
            schedule_posting_add = SchedulePostingAdd(
                workpost_id=workpost.id,
                clip_id=random_clip.id,
                task_id="",
                status="",
            )

            schedule_posting = await self.schedule_posting.add(schedule_posting_add)

            curl = AuthService().decrypt_data(vk_account.encrypted_curl)
            access_token = TokenService.get_token_from_curl(curl, proxy.http)

            task = create_post.delay(
                workpost.id, access_token, schedule_posting.id, clip_data, proxy.http
            )

            schedule_posting_update_data = SchedulePostingUpdate(
                task_id=task.id,
                status="starting",
            )

            await self.schedule_posting.edit(schedule_posting_update_data,
                                             exclude_unset=True,
                                             id=schedule_posting.id)

        await self.session.commit()