import gzip
import yt_dlp
import requests
import time
import os
import re
import json
import subprocess
import shlex
from typing import List, Dict, Any, Optional
import vk_api
from vk_api.exceptions import ApiError

def download_clip_by_url(url: str, out_dir=".") -> str:
    downloaded_file = None

    def hook(d):
        nonlocal downloaded_file
        if d['status'] == 'finished':
            downloaded_file = d['filename']  # полный путь к файлу

    ydl_opts = {
        "outtmpl": f"{out_dir}/%(title)s.%(ext)s",
        "format": "best",
        "progress_hooks": [hook],
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return downloaded_file


def get_access_token_vk(token: str):
    url = "https://login.vk.com/?act=web_token"
    payload = {
        "version": "1",
        "app_id": "6222115",
        "access_token": token,
    }

    headers = {
        ":authority": "login.vk.com",
        ":method": "POST",
        ":path": "/?act=web_token",
        ":scheme": "https",
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "ru,en-GB;q=0.9,en;q=0.8,ru-RU;q=0.7,en-US;q=0.6",
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://vk.com",
        "referer": "https://vk.com/",
        "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
    }

    # Удаляем недопустимые псевдо-заголовки (они валидны только в HTTP/2, requests их не поддерживает)
    headers = {k: v for k, v in headers.items() if not k.startswith(":")}

    response = requests.post(url, data=payload, headers=headers)

    try:
        return response.json()
    except Exception:
        return {"status_code": response.status_code, "text": response.text}


def vk_api_get_owner_short_videos(owner_id: int, vk_session, count: int = 1, api_version: str = '5.251'):
    vk = vk_session.get_api()
    data = vk.shortVideo.getOwnerVideos(
        owner_id=owner_id,
        count=count,
    )
    print(f"shortvideo data: {data}")
    return data

def get_owner_short_videos(owner_id: int, access_token: str, count: int = 1, api_version: str = '5.251'):
    """
    Return VK’s hidden shortVideo.getOwnerVideos response for a USER’s clips.
    owner_id must be a positive user ID (not a negative community ID).
    """
    url = "https://api.vk.com/method/shortVideo.getOwnerVideos"  # ← note uppercase V in 'shortVideo'
    params = {
        'owner_id': owner_id,         # positive user ID only!
        'count': count,
        'access_token': access_token, # user token from vk.me / vkhost
        'v': api_version,
    }
    time.sleep(0.34)
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    print(f"shortvideo data: {data}")
    if 'error' in data:
        raise RuntimeError(f"VK API error: {data['error']}")
    return data['response']


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

    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    if 'error' in data:
        raise RuntimeError(f"VK API error: {data['error']}")
    return data['response']


def get_all_owner_short_videos(owner_id: int,
                               access_token: str,
                               api_version: str = '5.251',
                               max_count: int = None,
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
    total_count: int = max_count

    while True:
        resp = get_owner_short_videos_page(
            owner_id=owner_id,
            count=page_size,
            access_token=access_token,
            api_version=api_version,
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



def download_vk_clip(files: Dict[str, str],
                     save_dir: str = ".",
                     filename: str = None) -> str:
    """
    Скачивает клип по URL из поля files.

    :param files: словарь с ключами вида 'mp4_144','mp4_240','mp4_360','mp4_480','hls' и т.п.
    :param quality: какой ключ взять из files (по умолчанию 'mp4_480')
    :param save_dir: директория, куда сохранить файл
    :param filename: имя файла; если None — будет сгенерировано как <quality>.mp4
    :return: путь к сохранённому файлу
    """

    def best_quality_key(files: Dict[str, str]) -> Optional[str]:
        """
        Из словаря files выбирает ключ с наибольшим разрешением (mp4_NN).
        Если mp4_* ключей нет — возвращает 'hls' (если есть), иначе первый ключ.

        :param files: dict, например {
            'mp4_144': '…', 'mp4_240': '…', 'hls': '…', …
        }
        :return: ключ с наибольшим NN, например 'mp4_480'
        """
        best_k = None
        best_res = -1

        # Ищём все mp4_{число} ключи
        for k in files:
            m = re.match(r'^mp4_(\d+)$', k)
            if not m:
                continue
            res = int(m.group(1))
            if res > best_res:
                best_res = res
                best_k = k

        if best_k:
            return best_k

        # fallback: если нет mp4_*, берём hls, если есть
        if 'hls' in files:
            return 'hls'

        # иначе просто первый ключ
        return next(iter(files), None)

    quality = best_quality_key(files)

    url = files[quality]
    # Генерируем имя файла, если не задано
    if filename is None:
        ext = "mp4" if quality.startswith("mp4") else "m3u8"
        filename = f"vk_clip_{quality}.{ext}"
    path = os.path.join(save_dir, filename)

    # Делаем streaming-запрос
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        # Открываем файл для записи побайтово
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    return path

def wait_for_encoding(vk, video_id: int, owner_id: int, video_hash: str, max_retries=20, delay: float = 3):
    for i in range(max_retries):
        try:
            resp = vk.shortVideo.encodeProgress(video_id=video_id, owner_id=owner_id, hash=video_hash)
        except ApiError as e:
            print(f"VK API error {e.code}: {e.error['error_msg']}")
            time.sleep(delay)
            continue

        is_ready = resp.get('is_ready', False)
        percents = resp.get('percents', 0)
        print(f"[{i+1}/{max_retries}] Обработка видео: {percents}%")

        if is_ready:
            print("Видео готово!")
            return

        time.sleep(delay)

    raise TimeoutError("Видео не обработано за заданный интервал времени")


def upload_short_video(token: str, group_id: int, video_path: str):
    try:
        vk = vk_api.VkApi(token=token).get_api()
        file_size = os.path.getsize(video_path)

        # 1. Получаем upload URL
        print("1. Получаем upload URL...")
        upload_data = vk.shortVideo.create(
            group_id=group_id,  # Обязательно
            file_size=file_size,  # Обязательно
        )

        # 2. Загружаем шортс
        print("2. Загружаем шортс...")
        with open(video_path, 'rb') as f:
            response = requests.post(upload_data['upload_url'], files={'file': f})
        video_info = response.json()

        # 3. ВАЖНО: Добавляем задержку для обработки видео
        print("▶️ Ждём обработки...")
        print(video_info['owner_id'])
        print(video_info)
        wait_for_encoding(vk, video_info['video_id'], video_info['owner_id'], video_info['video_hash'], max_retries=20, delay=3)
        #print("3. Ждем обработки шортс (10 сек)...")
        #time.sleep(10)


        # 3.5 Редактируем описание
        print("3.5 Редактируем описание...")
        edit_result = vk.shortVideo.edit(
            video_id=video_info['video_id'],  # Обязательно
            owner_id=video_info['owner_id'],  # Обязательно
            description="Описание с #хештегами",  # Текст описания
            privacy_view='all',
            can_make_duet=1
        )
        # print("Результат редактирования:")
        # print(json.dumps(edit_result, indent=2))

        # 4. Публикуем шортс
        print("4. Публикуем шортс...")
        publish_result = vk.shortVideo.publish(
            video_id=video_info['video_id'],  # Обязательно
            owner_id=video_info['owner_id'],  # Обязательно
            license_agree=1,  # Обязательно
            publish_date=0,
            wallpost=1  # wallpost=0 если не нужно на стену
        )

        # print("\nОтвет метода shortVideo.publish:")
        # print(json.dumps(publish_result, indent=2))

        print("\nУСПЕХ! Шортс опубликован ✅")

        wall_post_id = None
        if 'video' in publish_result and 'wall_post_id' in publish_result['video']:
            wall_post_id = publish_result['video']['wall_post_id']
        elif 'wall_post_id' in publish_result:
            wall_post_id = publish_result['wall_post_id']

        print(" ")
        print(f"Пост ID: {wall_post_id}")
        print(f"Ссылка: https://vk.com/wall-{group_id}_{wall_post_id}")

    except ApiError as e:
        print(f"\nОшибка VK API {e.code}: {e.error['error_msg']}")
        if e.code == 100:
            print("Ошибка VK API: Проверьте обязательные параметры:")
        elif e.code == 3001:
            print("Ошибка VK API: Видео еще не обработано. Увеличьте время ожидания")
        elif e.code == 9:
            print("Ошибка VK API 9: Flood control. Слишком много загрузок Shorts.")
        else:
            raise
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {str(e)}")

def get_vk_session_by_log_pass(login: str, password: str):
    print(login, password)
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

def get_vk_access_token_from_curl(curl_str: str, timeout: int = 30) -> str:
    cmd_list = shlex.split(curl_str)

    try:
        # Запускаем cURL и получаем ответ
        result = subprocess.run(
            cmd_list,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout
        )

        # Проверяем, является ли ответ gzip-сжатым
        if result.stdout.startswith(b'\x1f\x8b'):
            # Декодируем gzip
            try:
                raw = gzip.decompress(result.stdout)
                output = raw.decode('utf-8')
            except Exception as e:
                print(f"Ошибка при распаковке gzip: {e}")
                return None
        else:
            output = result.stdout.decode('utf-8')

        # Парсим JSON
        try:
            data = json.loads(output)
            return data.get('data', {}).get('access_token')
        except json.JSONDecodeError:
            print("Ошибка парсинга JSON")
            return None

    except subprocess.CalledProcessError as e:
        print("cURL error:\n", e.stderr.decode('utf-8'))
    except subprocess.TimeoutExpired:
        print("cURL command timed out")
    except Exception as e:
        print(f"Произошла ошибка: {e}")

    return None

def get_curl_from_file(curl_file_path: str = 'curl.txt',
                                  timeout: int = 30) -> Optional[str]:
    parts = []
    with open(curl_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip()
            # если строка заканчивается на бэкслеш — убираем его и продолжаем
            if line.endswith('\\'):
                parts.append(line[:-1].strip() + ' ')
            else:
                parts.append(line + ' ')
    cmd_str = ''.join(parts).strip()
    return cmd_str

def get_vk_access_token_from_file(curl_file_path: str = 'curl.txt',
                                  timeout: int = 30) -> Optional[str]:
    # 1. Считываем и склеиваем строки, игнорируя '\' в конце строк
    parts = []
    with open(curl_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip()
            # если строка заканчивается на бэкслеш — убираем его и продолжаем
            if line.endswith('\\'):
                parts.append(line[:-1].strip() + ' ')
            else:
                parts.append(line + ' ')
    cmd_str = ''.join(parts).strip()

    # 2. Безопасно разбираем строку в список аргументов
    cmd_list = shlex.split(cmd_str)

    try:
        # 3. Запускаем subprocess без shell=True
        result = subprocess.run(
            cmd_list,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout
        )
        output = result.stdout.decode('utf-8')
        data = json.loads(output)  # Парсим JSON
        return data.get('data', {}).get('access_token')
    except subprocess.CalledProcessError as e:
        print("cURL error:\n", e.stderr.decode('utf-8'))
    except subprocess.TimeoutExpired:
        print("cURL command timed out")
    except json.JSONDecodeError:
        print("Ошибка парсинга JSON")
    return None
