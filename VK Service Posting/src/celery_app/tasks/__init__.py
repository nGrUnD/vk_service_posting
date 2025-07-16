#from .post_tasks import *
#from .media_tasks import
from src.celery_app.tasks.tasks import *
from src.celery_app.tasks.vk_api import *
from src.celery_app.tasks.vk_account_parse import *
from src.celery_app.tasks.vk_group_parse import *
from src.celery_app.tasks.db_update_vk_account import *
from src.celery_app.tasks.db_update_vk_account_group import *
from src.celery_app.tasks.vk_group_source import *
from src.celery_app.tasks.workerpost import *
from src.celery_app.tasks.posting import *
from src.celery_app.tasks.vk_account_backup import *