from celery import Celery
from src.celery_app import celery_config
from kombu import Queue

app = Celery('tasks')
app.config_from_object('src.celery_app.celery_config')

# Автоматическое обнаружение задач в подмодулях
app.autodiscover_tasks(packages=['src.celery_app.tasks'])

app.conf.task_queues = (
    Queue("default"),
    Queue("heavy"),
)

# Маршрутизация: Selenium / тяжёлые задачи → очередь 'heavy' (см. worker celery-heavy)
app.conf.task_routes = {
    'vk_account_autocurl': {'queue': 'heavy'},
    'vk_checker_add_account': {'queue': 'heavy'},
}

app.conf.task_default_queue = 'default'