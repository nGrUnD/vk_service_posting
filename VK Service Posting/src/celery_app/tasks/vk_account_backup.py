import random
import time

from sqlalchemy import select

from src.celery_app import app
from src.celery_app.celery_db import SyncSessionLocal
from src.celery_app.tasks.db_update_vk_account import _update_vk_account_db
from src.models.proxy import ProxyOrm
from src.models.vk_account import VKAccountOrm
from src.vk_api_methods.vk_auth import get_token

def get_token_with_proxy_retry(database_manager, account_id_database: int, login: str, password: str, proxy: str = None, retries: int = 10):
    last_proxy = proxy
    current_proxy = proxy
    with database_manager as session:
        stmt = select(VKAccountOrm).where(VKAccountOrm.id == account_id_database)
        result = session.execute(stmt)
        vk_account_database = result.scalars().one_or_none()
        if vk_account_database is None:
            raise ValueError(f"VkAccount с логином {login} не найден в базе")

        for attempt in range(1, retries + 1):
            try:
                token = get_token(login=login, password=password, proxy_http=last_proxy)
                if not token:
                    raise Exception("Not get token")

                if last_proxy and last_proxy != current_proxy:
                    # Находим объект Proxy в базе
                    stmt_proxy = select(ProxyOrm).where(ProxyOrm.http == current_proxy)
                    proxy_db = session.execute(stmt_proxy).scalars().one_or_none()
                    if proxy_db:
                        vk_account_database.proxy_id = proxy_db.id
                        session.commit()

                return token

            except Exception as e:
                print(f"Ошибка: {e}")
                print(f"Попытка {attempt}: ошибка авторизации, пробуем другой прокси")
                stmt_proxies = select(ProxyOrm).where(ProxyOrm.http != current_proxy)
                proxies = session.execute(stmt_proxies).scalars().all()

                if not proxies:
                    print("Нет доступных прокси для смены. Повторяем попытку с текущим прокси.")
                    continue

                current_proxy = random.choice(proxies).http
                time.sleep(60)

    raise ValueError(f"Не удалось авторизоваться после {retries} попыток")


def update_db_vk_account(database_manager, vk_account_id_database: int, data: dict, count_groups: int):
    with database_manager as session:
        stmt = select(VKAccountOrm).where(VKAccountOrm.id == vk_account_id_database)
        result = session.execute(stmt)
        account = result.scalars().one_or_none()

        if not account:
            raise ValueError(f"Account {vk_account_id_database} not found")

        #account.vk_account_id = data['vk_account_id']
        #account.name = data['name']
        #account.second_name = data['second_name']
        #account.vk_account_url = data['vk_account_url']
        #account.avatar_url = data['avatar_url']
        account.groups_count = count_groups
        account.parse_status = "success"

        session.commit()


@app.task(bind=True, max_retries=999, default_retry_delay=60)
def get_vk_account_cred(self, account_id_database: int, login: str, password: str, proxy: str):
    database_manager = SyncSessionLocal()
    try:
        token = get_token_with_proxy_retry(database_manager, account_id_database, login, password, proxy)
        if not token:
            raise Exception("Not get token")

        data = {
            "token": token,
            "vk_account_id_database": account_id_database,
            "proxy": proxy,
        }

        update_db_vk_account(database_manager, account_id_database, data, 0)

    except Exception as exc:
        print(f"Ошибка: {exc}")
        if "не найден в базе" in str(exc):
            raise exc
        # При ошибке обновляем статус и имя
        if self.request.retries >= self.max_retries:
            error_data = {
                "parse_status": "failed",
                "name": "failed flood_control",
                "second_name": "failed flood_control",
                "flood_control": True,
            }
            _update_vk_account_db(account_id_database=account_id_database, account_update_data=error_data, groups_count=0)
            raise Exception("Max retries exceeded")

        # Можно логировать ошибку, например:
        self.retry(countdown=600)  # если хотите повторять задачу
        # Или просто вернуть ошибку без повторов:
        #raise

        # Если не нужно повторять, раскомментируйте raise и удалите self.retry