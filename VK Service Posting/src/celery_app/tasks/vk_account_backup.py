import random
import time

from sqlalchemy import select

from src.celery_app import app
from src.celery_app.celery_db import SyncSessionLocal
from src.celery_app.tasks.db_update_vk_account import _update_vk_account_db
from src.models.proxy import ProxyOrm
from src.models.vk_account import VKAccountOrm
from src.services.auth import AuthService
from src.vk_api_methods.vk_account import get_vk_account_data, get_vk_session_by_log_pass
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


def get_vk_account_data_retry(vk_account_id_db: int, proxy: str, retries: int = 10):
    last_proxy = proxy
    with SyncSessionLocal() as session:
        stmt = select(VKAccountOrm).where(VKAccountOrm.id == vk_account_id_db)
        result = session.execute(stmt)
        vk_account_database = result.scalars().one_or_none()

        if vk_account_database is None:
            raise ValueError(f"VkAccount с id {vk_account_database} не найден в базе")


        login = vk_account_database.login
        password = AuthService().decrypt_data(vk_account_database.encrypted_password)

        for attempt in range(1, retries + 1):
            try:
                vk_session = get_vk_session_by_log_pass(login=login, password=password, proxy=last_proxy)
                token_data = vk_session.token
                token = token_data['access_token']
                vk_account_data = get_vk_account_data(token, proxy)


                return vk_account_data, token
            except Exception as e:
                print(e)
                print(f"Попытка {attempt}: ошибка авторизации")

    raise ValueError(f"Не удалось авторизоваться после {retries} попыток")


def parse_vk_profile(vk_token, vk_account_id_database: int, proxy: str) -> dict:
    try:
        vk_account_data = get_vk_account_data(vk_token, proxy)
    except Exception as e:
        print(e)
        vk_account_data, token = get_vk_account_data_retry(vk_account_id_database, proxy)


    vk_account_id = vk_account_data["id"]
    vk_count_groups = 0
    vk_link = f"https://vk.com/id{vk_account_id}"

    vk_account_data = {
        "vk_account_id": vk_account_id,
        "name": vk_account_data["name"],
        "second_name": vk_account_data["second_name"],
        "vk_account_url": vk_link,
        "avatar_url": vk_account_data["avatar_url"],
        "groups_count": vk_count_groups,
    }

    return vk_account_data

def update_db_vk_account(database_manager, vk_account_id_database: int, data: dict, count_groups: int):
    with database_manager as session:
        stmt = select(VKAccountOrm).where(VKAccountOrm.id == vk_account_id_database)
        result = session.execute(stmt)
        account = result.scalars().one_or_none()

        if not account:
            raise ValueError(f"Account {vk_account_id_database} not found")

        account.vk_account_id = data['vk_account_id']
        account.name = account.login
        account.second_name = ""
        account.vk_account_url = data['vk_account_url']
        account.avatar_url = data['avatar_url']
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

        vk_account_data = parse_vk_profile(token, account_id_database, proxy)
        update_db_vk_account(database_manager, account_id_database, vk_account_data, 0)

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