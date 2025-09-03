import logging

import requests
from vk_api import vk_api

from src.utils.rand_user_agent import get_random_user_agent


def get_token(login, password, proxy_http: str = None):
    user_agent = get_random_user_agent()
    if proxy_http:
        session = requests.Session()
        session.proxies.update({
            "http": proxy_http,
            "https": proxy_http
        })
        session.headers.update({
            "User-Agent": (
                user_agent
            )
        })
        vk_session = vk_api.VkApi(login=login, password=password, session=session, app_id=6287487)
    else:
        vk_session = vk_api.VkApi(login=login, password=password, app_id=6287487)

    vk_session.load_cookie()
    vk_session.load_token()

    if not vk_session.is_sid() and not vk_session.token:
        try:
            vk_session.auth(token_only=True)
        except vk_api.AuthError as e:
            logging.error(e)
            return None

        session = vk_session.http  # requests.Session с живыми cookie
    else:
        logging.info("Живые куки")
        session = vk_session.http  # requests.Session с живыми cookie

    current_token = vk_session.token['access_token']

    logging.info(f'Текущий токен: {current_token}')
    logging.info(f'Cookie remixsid: {session.cookies}')

    # 3. Делаем запрос на обновление токена
    url = 'https://login.vk.com/'
    params = {
        'act': 'web_token',
        'version': 1,
        'app_id': 6287487,
        'access_token': current_token,
    }

    headers = {
        'User-Agent': user_agent,
        'Referer': 'https://vk.com/',
        'Origin': 'https://vk.com',
    }

    resp = session.get(url, params=params, headers=headers, allow_redirects=False)

    logging.info(f'Status: {resp.status_code}')
    logging.info(f'Ответ: {resp.text}')

    try:
        data = resp.json()
        new_token = data['data']['access_token']
        logging.info(f'Новый токен: {new_token}')
        return new_token, session.cookies
    except Exception as e:
        logging.error(f'Не удалось распарсить JSON: {e}')

    return None, None


def get_new_token(old_token: str, cookie, proxy_http: str = None):
    user_agent = get_random_user_agent()
    session = requests.Session()
    if proxy_http:
        session.proxies.update({
            "http": proxy_http,
            "https": proxy_http
        })
    print(f'proxy_http: {proxy_http}')


    session.headers.update({
        "User-Agent": (
            user_agent
        )
    })
    session.cookies = cookie

    logging.info(f'Текущий токен: {old_token}')
    logging.info(f'Текущий cookies: {session.cookies}')

    # 3. Делаем запрос на обновление токена
    url = 'https://login.vk.com/'
    params = {
        'act': 'web_token',
        'version': 1,
        'app_id': 6287487,
        'access_token': old_token,
    }

    headers = {
        'User-Agent': user_agent,
        'Referer': 'https://vk.com/',
        'Origin': 'https://vk.com',
    }

    resp = session.get(url, params=params, headers=headers, allow_redirects=False)

    # Логируем статус код и содержимое ответа для отладки
    logging.info(f'Статус код ответа: {resp.status_code}')
    logging.info(f'Содержимое ответа: {resp.text[:500]}...')  # Первые 500 символов

    # Проверяем статус код
    if resp.status_code != 200:
        logging.error(f'Неожиданный статус код: {resp.status_code}')
        return None

    try:
        # Проверяем, что ответ содержит JSON
        if not resp.text.strip():
            logging.error('Пустой ответ от сервера')
            return None

        data = resp.json()
        logging.info(f'Структура ответа: {data}')

        # Проверяем наличие нужных ключей
        if 'data' not in data:
            logging.error(f'Ключ "data" отсутствует в ответе. Доступные ключи: {list(data.keys())}')
            return None

        if 'access_token' not in data['data']:
            logging.error(f'Ключ "access_token" отсутствует в data. Доступные ключи: {list(data["data"].keys())}')
            return None

        new_token = data['data']['access_token']
        logging.info(f'Новый токен получен успешно')
        return new_token

    except requests.exceptions.JSONDecodeError as e:
        logging.error(f'Ошибка декодирования JSON: {e}')
        logging.error(f'Содержимое ответа: {resp.text}')
    except KeyError as e:
        logging.error(f'Отсутствует ключ в JSON: {e}')
        logging.error(f'Структура ответа: {data}')
    except Exception as e:
        logging.error(f'Неожиданная ошибка: {e}')
        logging.error(f'Тип ошибки: {type(e).__name__}')

    return None

def get_new_token_request(access_token: str, cookie: str, proxy: str = None):
    user_agent = get_random_user_agent()
    session = requests.Session()
    print(f'Proxy: {proxy}')
    session.proxies.update({
        "http": proxy,
        "https": proxy
    })

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": cookie,
        'Referer': 'https://vk.com/',
        'Origin': 'https://vk.com',
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "User-Agent": user_agent,
        "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }
    url = "https://login.vk.com/?act=web_token"
    data = {
        'version': 1,
        'app_id': 6287487,
        'access_token': access_token,
    }

    resp = session.post(url, params=data, headers=headers, allow_redirects=False)
    print(resp.text)
    try:
        resp_json = resp.json()
        new_token = resp_json['data']['access_token']
        print(f'Новый токен: {new_token}')
        return new_token
    except Exception as e:
        print(f'Не удалось распарсить JSON: {e}')
