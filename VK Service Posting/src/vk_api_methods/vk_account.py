import logging
import time

import requests

from src.services.vk_token_service import TokenService
from src.utils.rand_user_agent import get_random_user_agent
from src.vk_api_methods.vk_clip import get_clips_counts_for_groups
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

    proxy_response = None
    if proxy is not None:
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