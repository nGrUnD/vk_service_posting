# src/models/__init__.py

from src.models.user import UserOrm
from src.models.vk_account import VKAccountOrm
from src.models.proxy import ProxyOrm
from src.models.vk_group import VKGroupOrm
from src.models.vk_clip import VKClipOrm
from src.models.celery_task import CeleryTaskOrm
from src.models.workerpost import WorkerPostOrm
from src.models.schedule_posting import SchedulePostingOrm
from src.models.category import CategoryOrm
from src.models.clip_list import ClipListOrm
from src.models.vk_account_group import VKAccountGroupOrm