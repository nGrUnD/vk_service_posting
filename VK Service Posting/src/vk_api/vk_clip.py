from typing import List, Dict, Any

import requests
import time

from pycparser.ply.yacc import token

from src.services.vk_token_service import TokenService
import vk_api
from src.utils.rand_user_agent import get_random_user_agent

def is_token_expired(access_token: str) -> bool:
    """
    Проверка валидности токена VK.
    Делает запрос к методу users.get — если ошибка 5 (User authorization failed), значит токен протух.
    """
    params = {
        'access_token': access_token,
        'v': '5.251',
        'user_ids': '1'
    }
    response = requests.get('https://api.vk.com/method/users.get', params=params)
    data = response.json()
    if 'error' in data and data['error']['error_code'] == 5:
        return True
    return False

def get_owner_short_videos(owner_id: int, access_token: str) -> dict:
    url = "https://api.vk.com/method/video.get"
    params = {
        "access_token": access_token,
        "v": "5.131",
        "owner_id": -owner_id,  # Для групп VK owner_id — отрицательное значение
        "count": 1,
        "filters": "short_videos"
    }

    time.sleep(0.34)
    headers = {"User-Agent": get_random_user_agent()}
    response = requests.get(url, params=params, headers=headers)
    data = response.json()

    if "error" in data:
        raise Exception(f"Ошибка при получении short_videos: {data['error']['error_msg']}")

    return data.get("response", {})


    #return [API.shortVideo.getOwnerVideos({"owner_id":-226848921"count":10}),
    #        API.shortVideo.getOwnerVideos({"owner_id":-226848921"count":10})]
def get_clips_counts_for_groups(group_ids: list[int], access_token: str, proxy: str) -> dict[int, int]:
    """
    Использует VK API `execute`, чтобы получить clips_count для каждой группы.
    Возвращает словарь {group_id: clips_count}.
    """
    assert len(group_ids) <= 25, "Максимум 25 групп за один вызов execute"
    proxy_response = None
    if proxy is not None:
        proxy_response = {
            "http": proxy,
            "https": proxy,
        }

    # Формируем список вызовов API.shortVideo.getOwnerVideos
    code_calls = ','.join(
        f'API.shortVideo.getOwnerVideos({{"owner_id":{-gid},"count":1}})' for gid in group_ids
    )

    code = f'return [{code_calls}];'

    url = "https://api.vk.com/method/execute"
    params = {
        "access_token": access_token,
        "v": "5.251",
        "code": code
    }

    headers = {
        "User-Agent": get_random_user_agent()
    }

    response = requests.post(url, data=params, headers=headers, proxies=proxy_response)
    data = response.json()
    #print(data)

    if "error" in data:
        raise Exception(f"VK execute error: {data['error']['error_msg']}")

    # Собираем результат в словарь {group_id: count}
    # Ответ будет списком с объектами, где есть `count`
    result = {}
    for gid, clip_response in zip(group_ids, data["response"]):
        result[gid] = clip_response.get("count", 0)

    return result

def get_owner_short_videos_page(owner_id: int,
                                count: int,
                                access_token: str,
                                api_version: str = '5.251',
                                start_from: str = None) -> Dict[str, Any]:
    """
    Один “скролл” — забирает страницу клипов (до `count` штук) с опциональным курсором start_from.
    Возвращает словарь с ключами 'response': {'items', 'count', 'next_from'}.
    """
    url = 'https://api.vk.com/method/shortVideo.getOwnerVideos'
    params = {
        'owner_id': owner_id,
        'count': count,
        'access_token': access_token,
        'v': api_version
    }
    if start_from:
        params['start_from'] = start_from

    headers = {"User-Agent": get_random_user_agent()}
    resp = requests.get(url, params=params, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    if 'error' in data:
        raise RuntimeError(f"VK API error: {data['error']}")
    return data['response']

def vk_api_get_owner_short_videos(owner_id: int, vk_session, count: int = 1, start_from: str = None, api_version: str = '5.251'):
    vk = vk_session.get_api()
    data = vk.shortVideo.getOwnerVideos(
        owner_id=owner_id,
        count=count,
        start_from=start_from,
    )
    print(f"shortvideo data: {data}")
    return data


def get_all_owner_short_videos(owner_id: int,
                               access_token: str,
                               api_version: str = '5.251',
                               page_size: int = 100,
                               delay: float = 0.34) -> List[Dict[str, Any]]:
    """
    Собирает информацию обо всех коротких видео владельца (паблика или пользователя).

    :param max_count:
    :param owner_id: ID владельца ( >0 — пользователь, <0 — сообщество)
    :param access_token: токен доступа VK API
    :param api_version: версия VK API
    :param page_size: сколько записей запрашивать за раз (макс 100)
    :param delay: задержка между запросами (сек)
    :return: список всех items
    """
    all_items: List[Dict[str, Any]] = []
    start_from: str = None
    total_count: int = None

    vk_session = vk_api.VkApi(token=access_token)
    vk_session.api_version="5.251"
    vk_session.app_id=6287487

    while True:
        #print(total_count)

        if is_token_expired(access_token):
            #access_token = TokenService.get_token_from_curl(curl)
            print("Токену пизда пришла")

        resp = vk_api_get_owner_short_videos(
            owner_id=owner_id,
            count=page_size,
            vk_session=vk_session,
            start_from=start_from
        )

        # Сохраняем общее число записей один раз
        if total_count is None:
            total_count = resp.get('count', 0)

        items = resp.get('items', [])
        all_items.extend(items)

        # Отладочный вывод
        print(f"Fetched {len(items)} items, total so far: {len(all_items)}/{total_count}")

        # Готовимся к следующей странице
        start_from = resp.get('next_from')
        if not start_from:
            break  # больше страниц нет

        if len(all_items) >= total_count:
            break

        # Задержка чтобы не превысить rate limit
        time.sleep(delay)

    print(f"Finished: collected {len(all_items)} of {total_count} items.")
    return all_items
