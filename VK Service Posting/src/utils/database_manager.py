from src.repositories.category import CategoryRepository
from src.repositories.celery_task import CeleryTaskRepository
from src.repositories.clip_list import ClipListRepository
from src.repositories.proxy import ProxyRepository
from src.repositories.schedule_posting import SchedulePostingRepository
from src.repositories.user import UserRepository
from src.repositories.vk_account import VKAccountRepository
from src.repositories.vk_account_group import VKAccountGroupRepository
from src.repositories.vk_clip import VKClipRepository
from src.repositories.vk_group import VKGroupRepository
from src.repositories.workerpost import WorkerPostRepository


class DataBaseManager:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def __aenter__(self):
        self.session = self.session_factory()

        self.user = UserRepository(self.session)
        self.vk_account = VKAccountRepository(self.session)
        self.category = CategoryRepository(self.session)
        self.vk_group = VKGroupRepository(self.session)
        self.celery_task = CeleryTaskRepository(self.session)
        self.clip_list = ClipListRepository(self.session)
        self.vk_clip = VKClipRepository(self.session)
        self.workerpost = WorkerPostRepository(self.session)
        self.schedule_posting = SchedulePostingRepository(self.session)
        self.proxy = ProxyRepository(self.session)
        self.vk_account_group = VKAccountGroupRepository(self.session)

        return self

    async def __aexit__(self, *args):
        await self.session.rollback()
        await self.session.close()

    async def commit(self):
        await self.session.commit()