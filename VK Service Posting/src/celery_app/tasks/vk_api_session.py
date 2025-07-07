import random

from sqlalchemy import select

from src.celery_app import app
from src.celery_app.celery_db import SyncSessionLocal
from src.celery_app.tasks.db_update_vk_account import _update_vk_account_db
from src.models.proxy import ProxyOrm
from src.models.vk_account import VKAccountOrm
from src.vk_api.vk_account import get_vk_session_by_log_pass


def get_vk_session_with_retry(database_manager, account_id_database: int, login: str, password: str, proxy: str = None, retries: int = 10):
    last_proxy = proxy
    with database_manager as session:
        stmt = select(VKAccountOrm).where(VKAccountOrm.id == account_id_database)
        result = session.execute(stmt)
        vk_account_database = result.scalars().one_or_none()
        if vk_account_database is None:
            raise ValueError(f"VkAccount с логином {login} не найден в базе")

        for attempt in range(1, retries + 1):
            try:
                vk_session = get_vk_session_by_log_pass(login=login, password=password, proxy=last_proxy)

                stmt = select(ProxyOrm).where(ProxyOrm.id == vk_account_database.proxy_id)
                result = session.execute(stmt)
                proxy_vk_account_db = result.scalars().one_or_none()
                if last_proxy and last_proxy != proxy_vk_account_db.http:
                    # Находим объект Proxy в базе
                    stmt_proxy = select(ProxyOrm).where(ProxyOrm.http == last_proxy)
                    proxy_db = session.execute(stmt_proxy).scalars().one_or_none()
                    if proxy_db:
                        vk_account_database.proxy_id = proxy_db.id
                        session.commit()

                return vk_session
            except Exception as e:
                print("Ошибка: {e}")
                print(f"Попытка {attempt}: ошибка авторизации, пробуем другой прокси")
                stmt_proxies = select(ProxyOrm).where(ProxyOrm.http != last_proxy)
                proxies = session.execute(stmt_proxies).scalars().all()

                if not proxies:
                    print("Нет доступных прокси для смены. Повторяем попытку с текущим прокси.")
                    continue

                last_proxy = random.choice(proxies).http

    raise ValueError(f"Не удалось авторизоваться после {retries} попыток")


@app.task(bind=True)
def get_vk_account_cred(self, account_id_database: int, login: str, password: str, proxy: str) -> dict:
    try:
        #print(f"Proxy: {proxy}")
        database_manager = SyncSessionLocal()
        vk_session = get_vk_session_with_retry(
            database_manager=database_manager,
            account_id_database=account_id_database,
            login=login,
            password=password,
            proxy=proxy,
        )

        #vk_session = get_vk_session_by_log_pass(login, password, proxy)
        vk_token = vk_session.token['access_token']
        data = {
            "token": vk_token,
            "vk_account_id_database": account_id_database,
            "proxy": proxy,
        }

        _update_vk_account_db(account_id_database=account_id_database, account_update_data=data, groups_count=0)

        return data

    except Exception as exc:
        # При ошибке обновляем статус и имя
        error_data = {
            "parse_status": "failed",
            "name": "failed flood_control",
            "second_name": "failed flood_control",
            "flood_control": True,
        }
        _update_vk_account_db(account_id_database=account_id_database, account_update_data=error_data, groups_count=0)

        # Можно логировать ошибку, например:
        #self.retry(exc=exc, countdown=60, max_retries=3)  # если хотите повторять задачу
        # Или просто вернуть ошибку без повторов:
        raise

        # Если не нужно повторять, раскомментируйте raise и удалите self.retry