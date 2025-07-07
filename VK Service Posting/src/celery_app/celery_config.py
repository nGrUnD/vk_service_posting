from src.config import settings

redis_password = settings.REDIS_PASSWORD
broker_url = f'redis://:{redis_password}@redis:6379/0'
result_backend = f'redis://:{redis_password}@redis:6379/1'
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'Europe/Moscow'
enable_utc = True
worker_concurrency = 20  # Работает до 50 задач параллельно в каждом worker
worker_prefetch_multiplier = 10  # Берёт 5 задачи за раз, пока обрабатывает
worker_max_tasks_per_child = 50  # Перезапускает процесс после 50 задач nano VK Service Posting/src/celery_app/celery_config.py