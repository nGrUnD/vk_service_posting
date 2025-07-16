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

    if not vk_session.check_sid():
        try:
            vk_session.auth()
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
        return new_token
    except Exception as e:
        logging.error(f'Не удалось распарсить JSON: {e}')

    return None
