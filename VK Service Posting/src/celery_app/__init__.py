from celery import Celery
from src.celery_app import celery_config

app = Celery('tasks')
app.config_from_object('src.celery_app.celery_config')

# Автоматическое обнаружение задач в подмодулях
app.autodiscover_tasks(packages=['src.celery_app.tasks'])