import logging
import time

import requests

from src.services.vk_token_service import TokenService
from src.utils.rand_user_agent import get_random_user_agent
from src.vk_api_methods.vk_auth import get_new_token_request
from src.vk_api_methods.vk_clip import get_clips_counts_for_groups, is_token_expired
from vk_api import vk_api


def get_vk_session_by_token(token: str, proxy: str = None):
    if proxy:
        session = requests.Session()
        session.proxies.update({
            'http': proxy,
            'https': proxy
        })
        vk_session = vk_api.VkApi(token=token, session=session)
    else:
        vk_session = vk_api.VkApi(token=token)

    vk_session.api_version="5.251"
    vk_session.app_id=6287487

    return vk_session

def get_vk_session_by_log_pass(login: str, password: str, proxy: str = None):
    #print(login, password)
    if proxy:
        session = requests.Session()
        session.proxies.update({
            'http': proxy,
            'https': proxy
        })
        session.headers.update({
            "User-Agent": (get_random_user_agent())
        })
        vk_session = vk_api.VkApi(login=login, password=password, session=session)
    else:
        vk_session = vk_api.VkApi(login=login, password=password)
    vk_session.api_version="5.251"
    vk_session.app_id=6287487
    vk_session.token = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef01234"
    try:
        vk_session.auth()
    except vk_api.AuthError as error_msg:
        print(error_msg)
        raise error_msg

    print(vk_session.api_version)
    print(vk_session.app_id)
    #vk = vk_auth.get_api()
    return vk_session


def get_vk_account_data(access_token: str, proxy: str = None):
    # URL для запроса данных аккаунта
    url = "https://api.vk.com/method/users.get"

    # Параметры запроса
    params = {
        "access_token": access_token,
        "v": "5.131",  # Версия API
        "fields": "photo_200"  # Поля, которые нужно получить
    }

    print(f'Proxy: {proxy}')
    proxy_response = {
        "http": proxy,
        "https": proxy,
    }

    # Отправка запроса
    headers = {"User-Agent": get_random_user_agent()}
    response = requests.get(url, params=params, headers=headers, proxies=proxy_response)
    data = response.json()

    # Проверка на ошибки
    if "error" in data:
        raise Exception(f"Ошибка при получении данных: {data['error']['error_msg']}")

    # Извлечение данных
    user_data = data["response"][0]
    id = user_data["id"]
    name = user_data["first_name"]
    second_name = user_data["last_name"]
    avatar_url = user_data["photo_200"]
    print(user_data)

    return {
        "id": id,
        "name": name,
        "second_name": second_name,
        "avatar_url": avatar_url,
    }

def get_vk_account_admin_groups(access_token: str, user_id: int, proxy: str) -> dict:
    url = "https://api.vk.com/method/groups.get"
    version = "5.131"
    delay = 0.34
    count_per_request = 1000

    headers = {"User-Agent": get_random_user_agent()}
    proxy_response = None
    if proxy is not None:
        proxy_response = {
            "http": proxy,
            "https": proxy,
        }

    all_items = []
    offset = 0

    params = {
        "access_token": access_token,
        "v": version,
        "extended": 1,
        "user_id": user_id,
        "filter": "admin",
        "count": count_per_request,
        "offset": offset,
        "fields": "photo_200"
    }

    # Первый запрос
    response = requests.get(url, params=params, headers=headers, proxies=proxy_response)
    response_json = response.json()

    if "error" in response_json:
        raise Exception(f"Ошибка при получении данных: {response_json['error']['error_msg']}")

    data = response_json["response"]
    total_count = data["count"]
    all_items.extend(data["items"])

    # Остальные запросы
    while offset + count_per_request < total_count:
        offset += count_per_request
        params["offset"] = offset
        time.sleep(delay)


        response = requests.get(url, params=params, headers=headers, proxies=proxy_response)
        response_json = response.json()

        if "error" in response_json:
            if "access_token has expired" in response_json['error']['error_msg']:
                #access_token = TokenService().get_token_from_curl(vk_session)
                print("Пизда токену")
                params["access_token"] = access_token
                response = requests.get(url, params=params, headers=headers, proxies=proxy_response)
                response_json = response.json()
            else:
                raise Exception(f"Ошибка при получении данных (offset={offset}): {response_json['error']['error_msg']}")

        data = response_json["response"]
        new_items = data.get("items", [])

        if not new_items:
            print("⚠️ Пустой ответ, останавливаемся.")
            break

        all_items.extend(new_items)
        print(f"Получено {len(all_items)} из {total_count}")

    # Форматируем результат
    groups = []
    batch_size = 25
    for i in range(0, len(all_items), batch_size):
        print(f"group admin get: {i} of {len(all_items)}")
        batch = all_items[i:i + batch_size]
        group_ids = [g["id"] for g in batch]

        try:
            clips_count_map = get_clips_counts_for_groups(group_ids, access_token, proxy)
        except Exception as e:
            clips_count_map = {gid: 0 for gid in group_ids}  # fallback

        for group in batch:
            group_id = group["id"]
            groups.append({
                "group_id": group_id,
                "vk_group_url": f"https://vk.com/club{group_id}",
                "avatar_url": group.get("photo_200"),
                "name": group.get("name"),
                "clips_count": clips_count_map.get(group_id, 0)
            })

    return {
        "count": total_count,
        "groups": groups,
    }

def get_vk_account_groups(access_token: str, user_id: int, proxy: str = None):
    """
    Получает все группы пользователя VK (не только админские),
    возвращает всю доступную базовую информацию о них.
    """
    url = "https://api.vk.com/method/groups.get"
    version = "5.131"
    delay = 0.34
    count_per_request = 1000

    headers = {"User-Agent": get_random_user_agent()}
    print(f'Proxy: {proxy}')
    proxy_response = {"http": proxy, "https": proxy}

    all_items = []
    offset = 0

    params = {
        "access_token": access_token,
        "v": version,
        "extended": 1,               # чтобы вернуть подробную информацию о группах
        "user_id": user_id,
        "count": count_per_request,
        "offset": offset,
        "fields": "photo_200"  # нужные поля
        # !! filter убираем, иначе будет только admin
    }

    # Первый запрос
    response = requests.get(url, params=params, headers=headers, proxies=proxy_response)
    response_json = response.json()

    if "error" in response_json:
        raise Exception(f"Ошибка при получении данных: {response_json['error']['error_msg']}")

    data = response_json["response"]
    total_count = data["count"]
    all_items.extend(data["items"])

    # Загружаем постранично
    while offset + count_per_request < total_count:
        offset += count_per_request
        params["offset"] = offset
        time.sleep(delay)

        response = requests.get(url, params=params, headers=headers, proxies=proxy_response)
        response_json = response.json()

        if "error" in response_json:
            if "access_token has expired" in response_json['error']['error_msg']:
                print("⛔ Токен протух")
                raise Exception("Требуется обновление access_token")
            else:
                raise Exception(f"Ошибка при получении данных (offset={offset}): {response_json['error']['error_msg']}")

        data = response_json["response"]
        new_items = data.get("items", [])

        if not new_items:
            print("⚠️ Пустой ответ, останавливаемся.")
            break

        all_items.extend(new_items)
        print(f"Получено {len(all_items)} из {total_count}")

    # Форматирование результата
    groups = []
    for group in all_items:
        group_id = group["id"]
        groups.append({
            "group_id": group_id,
            "vk_group_url": f"https://vk.com/{group.get('screen_name', f'club{group_id}')}",
            "avatar_url": group.get("photo_200"),
            "name": group.get("name"),
            #"type": group.get("type"),                # group / page / event
            #"activity": group.get("activity"),        # тип деятельности
            #"status": group.get("status"),            # статус/описание
            #"members_count": group.get("members_count"),
            #"description": group.get("description"),
        })

    return {
        "count": total_count,
        "groups": groups,
    }


def get_vk_group_info(access_token: str, vk_group_id: str, proxy: str = None):
    """
    Получает информацию об одной группе VK по её ID.

    :param access_token: токен доступа VK
    :param vk_group_id: ID группы (число или короткое имя, например "227197531" или "mygroup")
    :param proxy: прокси (опционально)
    :return: словарь с информацией о группе
    """
    url = "https://api.vk.com/method/groups.getById"
    version = "5.131"

    headers = {"User-Agent": get_random_user_agent()}
    print(f'Proxy: {proxy}')
    proxy_response = {"http": proxy, "https": proxy} if proxy else None

    params = {
        "access_token": access_token,
        "v": version,
        "group_id": vk_group_id,
        "fields": "photo_200,members_count,description"
    }

    response = requests.get(url, params=params, headers=headers, proxies=proxy_response)
    response_json = response.json()

    if "error" in response_json:
        error_msg = response_json['error']['error_msg']
        if "access_token has expired" in error_msg:
            print("⛔ Токен протух")
            raise Exception("Требуется обновление access_token")
        else:
            raise Exception(f"Ошибка при получении данных группы: {error_msg}")

    data = response_json.get("response")
    if not data or len(data) == 0:
        raise Exception(f"Группа с ID {vk_group_id} не найдена")

    group = data[0]
    group_id = group["id"]

    return {
        "group_id": group_id,
        "vk_group_url": f"https://vk.com/{group.get('screen_name', f'club{group_id}')}",
        "avatar_url": group.get("photo_200"),
        "name": group.get("name"),
        "members_count": group.get("members_count"),
        "description": group.get("description"),
    }