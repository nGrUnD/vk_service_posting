import shlex
import requests
from typing import Dict, Optional


class TokenRequest:
    def __init__(self, url: str, headers: Dict[str, str], data: Dict[str, str], cookies: Dict[str, str]):
        self.url = url
        self.headers = headers
        self.data = data
        self.cookies = cookies


class TokenService:
    @staticmethod
    def parse_curl(curl_cmd: str) -> TokenRequest:
        """
        Разбирает curl-команду и возвращает TokenRequest с url, headers, data и cookies.
        Поддерживается:
         - URL (включая query-параметры)
         - заголовки (-H / --header)
         - куки (-b / --cookie)
         - тело запроса (--data / --data-raw / -d)
        """
        parts = shlex.split(curl_cmd)
        url: Optional[str] = None
        headers: Dict[str, str] = {}
        data: Dict[str, str] = {}
        cookies: Dict[str, str] = {}

        it = iter(parts)
        for part in it:
            if part.lower() == 'curl':
                raw = next(it)
                url = raw.strip("'\"")
                # разбор query-параметров в data
                if '?' in url:
                    base, qs = url.split('?', 1)
                    url = base
                    for kv in qs.split('&'):
                        if '=' in kv:
                            k, v = kv.split('=', 1)
                            data[k] = v
            elif part in ('-H', '--header'):
                hdr = next(it)
                key, value = hdr.split(':', 1)
                key = key.strip()
                value = value.strip().strip("'\"")
                # обычный заголовок
                headers[key] = value
            elif part in ('-b', '--cookie'):
                cookie_str = next(it).strip("'\"")
                # строка может содержать несколько куки через ';'
                for pair in cookie_str.split(';'):
                    pair = pair.strip()
                    if '=' in pair:
                        ck, cv = pair.split('=', 1)
                        cookies[ck] = cv
            elif part in ('--data', '--data-raw', '-d'):
                body = next(it).strip("'\"")
                for kv in body.split('&'):
                    if '=' in kv:
                        k, v = kv.split('=', 1)
                        data[k] = v

        if not url:
            return None
        return TokenRequest(url, headers, data, cookies)

    @staticmethod
    def get_token_from_curl(vk_session, proxy: str = None) -> str:
        """
        Парсит curl_cmd, выполняет POST (с передачей cookies) и возвращает access_token.
        """
        req = TokenService.parse_curl(vk_session)
        if not req:
            return None

        # Для отладки можно раскомментировать:
        # print("URL:", req.url)
        # print("HEADERS:", req.headers)
        # print("DATA:", req.data)
        # print("COOKIES:", req.cookies)

        proxy_response = None
        if proxy is not None:
            proxy_response = {
                "http": proxy,
                "https": proxy,
            }

        # Выполняем запрос, передавая cookies отдельно
        resp = requests.post(
            req.url,
            headers=req.headers,
            data=req.data,
            cookies=req.cookies,
            proxies=proxy_response,
        )
        resp.raise_for_status()
        json_resp = resp.json()

        # Если VK вернул ошибку — выдаём её
        if 'error_info' in json_resp:
            raise RuntimeError(f"VK error: {json_resp['error_info']}")

        # Пробуем достать токен
        token = json_resp.get("data", {}).get("access_token")
        if not token:
            raise KeyError(f"Не найден access_token в ответе: {json_resp}")

        return token
