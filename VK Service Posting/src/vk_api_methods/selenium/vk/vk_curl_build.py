import time
import json
import urllib.parse
import re

TARGET_SCOPES = [
    'https://login.vk.com/*',
    'https://login.vk.ru/*',
    'https://api.vk.com/*',
]

ACCESS_TOKEN_RE = re.compile(r'(?:^|[?&])access_token=([^&\s\'"]+)', re.IGNORECASE)

def _has_access_token_in_url(url: str) -> str | None:
    m = ACCESS_TOKEN_RE.search(url)
    return m.group(1) if m else None

def _has_access_token_in_body(body_bytes: bytes | None) -> str | None:
    if not body_bytes:
        return None
    try:
        body_str = body_bytes.decode('utf-8', 'ignore')
    except Exception:
        return None
    # Ищем как urlencoded параметр
    m = ACCESS_TOKEN_RE.search(body_str)
    if m:
        return m.group(1)
    # Иногда токен может быть в JSON
    try:
        data = json.loads(body_str)
        # Поищем по значению
        if isinstance(data, dict):
            for k, v in data.items():
                if k.lower() == 'access_token' and isinstance(v, str):
                    return v
    except Exception:
        pass
    return None

def _quote_single(s: str) -> str:
    # Оборачиваем в одинарные кавычки, экранируя внутренние одинарные через '\'' (как делает Chrome)
    return "'" + s.replace("'", "'\"'\"'") + "'"

def _normalize_headers_for_curl(headers: dict[str, str]) -> tuple[list[str], str | None]:
    """
    Возвращает:
      - список -H для всех заголовков кроме Cookie
      - значение cookies (если есть) для -b
    """
    h_list = []
    cookie_value = None
    for k, v in headers.items():
        if k.lower() == 'cookie':
            cookie_value = v
            continue
        # selenium-wire иногда добавляет pseudo/служебные заголовки — их лучше отфильтровать, если попадутся
        h_list.append(f"-H {_quote_single(f'{k}: {v}')}")
    return h_list, cookie_value

def _body_to_curl_flags(req) -> list[str]:
    """
    Возвращает список флагов для тела запроса:
      --data-raw '...' для методов с телом.
    """
    flags = []
    body = getattr(req, 'body', None)
    if not body:
        return flags

    if isinstance(body, bytes):
        body_str = body.decode('utf-8', 'ignore')
        flags.append(f"--data-raw {_quote_single(body_str)}")
    elif isinstance(body, str):
        flags.append(f"--data-raw {_quote_single(body)}")
    elif isinstance(body, dict):
        # Превратим в x-www-form-urlencoded
        flags.append(f"--data-raw {_quote_single(urllib.parse.urlencode(body))}")
    return flags

def _request_to_curl(req) -> str:
    # Метод
    method = req.method.upper() if req.method else 'GET'
    # URL
    url = req.url

    # Заголовки
    headers = dict(req.headers or {})
    h_list, cookie_value = _normalize_headers_for_curl(headers)

    # Формируем части
    parts = ["curl"]
    parts.append(_quote_single(url))
    parts.append(f"-X {method}")

    # Cookie в -b (как чаще делает Chrome)
    if cookie_value:
        parts.append(f"-b {_quote_single(cookie_value)}")

    # Все остальные заголовки
    parts.extend(h_list)

    # Тело
    if method in ('POST', 'PUT', 'PATCH'):
        parts.extend(_body_to_curl_flags(req))

    return " ".join(parts)

def get_vk_curl_v2(driver, timeout: int = 300, reloadtime: int = 10) -> str | None:
    """
    Ждём запросы, в которых есть access_token.
    Приоритет:
      1) https://login.vk.(com|ru)/?act=web_token с access_token
      2) Любой запрос к https://api.vk.com/... с access_token
    Возвращает curl в стиле "Copy as cURL (bash)".
    """
    # Ограничим захват лишнего трафика
    try:
        driver.scopes = TARGET_SCOPES
    except Exception:
        pass

    driver.get("https://vk.ru/id0")

    end = time.time() + timeout
    last_seen_without_token = None

    timer_reload = 0
    while time.time() < end:
        # Обновляем список запросов на каждом шаге
        for req in driver.requests:
            if not getattr(req, 'response', None):
                # Ждём хотя бы ответа (часто бесполезно брать незавершённые)
                continue

            url = req.url or ""
            method = (req.method or "GET").upper()
            body = getattr(req, 'body', None)

            token = _has_access_token_in_url(url) or _has_access_token_in_body(body)

            # 1) web_token с токеном — лучший кандидат
            if 'login.vk.' in url and 'act=web_token' in url:
                if token:
                    return _request_to_curl(req)
                else:
                    # запомним, вдруг ничего лучше не найдём (для диагностики)
                    last_seen_without_token = req

            # 2) Любой метод API с токеном
            if 'api.vk.com/method/' in url and token:
                return _request_to_curl(req)

        time.sleep(0.3)
        timer_reload += 0.3
        if timer_reload > reloadtime:
            timer_reload = 0
            driver.refresh()

    # Если ничего не нашли — вернём последний web_token без токена (для отладки),
    # чтобы вы могли посмотреть сформированный curl и понять, что ещё перехватить.
    if last_seen_without_token:
        return _request_to_curl(last_seen_without_token)

    return None