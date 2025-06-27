import time
from time import sleep

from src.celery_app import app

@app.task
def long_running_task(data):
    print("Задача началась!")
    time.sleep(10)
    return f"Результат для данных: {data}"