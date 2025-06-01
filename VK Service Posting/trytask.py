import time

from src.celery_app.tasks.tasks import long_running_task
from src.celery_app.tasks.vk_api import get_vk_account_curl



def get_single_vk_account(file_path: str = 'vkaccount.txt', index: int = 0) -> tuple[str, str]:
    """
    Возвращает кортеж (login, password) для одной учётки из файла vkaccount.txt.
    По умолчанию берёт аккаунт с указанным индексом (0 — первый).
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        # Считаем все строки и сразу очистим их от лишнего
        lines = [line.strip() for line in f if line.strip()]
    try:
        line = lines[index]
    except IndexError:
        raise IndexError(f"No account at index {index}; file contains only {len(lines)} entries.")

    if ':' not in line:
        raise ValueError(f"Неправильный формат: {line!r}. Ожидается 'login:password'.")

    login, password = line.split(':', 1)
    return login, password


login, pwd = get_single_vk_account()
result = get_vk_account_curl.delay(login, pwd)

print(result.id)  # Выведите ID задачи для отслеживания
print(result.status)  # PENDING -> SUCCESS
print(result.status)  # PENDING -> SUCCESS
time.sleep(10)
print(result.status)  # PENDING -> SUCCESS
print(result.get())   # Получить результат (блокирует выполнение, пока задача не завершится)
print(result.status)  # PENDING -> SUCCESS
#print(result)