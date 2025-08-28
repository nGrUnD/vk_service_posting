import os
import re
import time
from typing import Dict, Optional

import yt_dlp
from vk_api import vk_api
import requests

from vk_api.vk_api import ApiError


def get_clip_info(owner_id: int, video_id: int, access_token: str, proxy: str) -> dict:
    """
    Получить полную информацию о конкретном клипе (с файлами).
    """
    url = "https://api.vk.com/method/execute"
    payload = {
        "code": f"""
        return API.video.get({{
            "videos": "{owner_id}_{video_id}",
            "extended": 1
        }});""",
        "access_token": access_token,
        "v": "5.253"
    }
    proxy_response = {
        "http": proxy,
        "https": proxy,
    }
    response = requests.post(url, data=payload, proxies=proxy_response)
    data = response.json()
    if "error" in data:
        raise Exception(data["error"]["error_msg"])

    result = data["response"]["items"][0]
    return result

#!===================  Скачивание клипа
def download_clip_by_url(url: str, owner_id: int, clip_id: int, out_dir=".") -> str:
    downloaded_file = None
    filename_template = f"{out_dir}/{owner_id}-{clip_id}.%(ext)s"

    def hook(d):
        nonlocal downloaded_file
        if d['status'] == 'finished':
            downloaded_file = d['filename']  # полный путь к файлу

    ydl_opts = {
        "outtmpl": filename_template,
        "format": "best",
        "progress_hooks": [hook],
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return downloaded_file



def download_vk_clip(files: dict[str, str],
                     vk_group_id: int,
                     vk_clip_id: int,
                     proxy: str,
                     save_dir: str = ".",
                     filename: str = None) -> str:
    """
    Скачивает клип по прямому URL.

    :param url: прямой URL к файлу
    :param save_dir: директория, куда сохранить файл
    :param filename: имя файла; если None — будет сгенерировано
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

    # например, -12345 для паблика
    # Генерируем имя файла, если не задано

    quality = best_quality_key(files)

    proxy_response = {
        "http": proxy,
        "https": proxy,
    }

    url = files[quality]
    if filename is None:
        ext = "mp4"
        filename = f"vk_clip_{vk_group_id}_{vk_clip_id}_{quality}.{ext}"
    path = os.path.join(save_dir, filename)

    with requests.get(url, stream=True, proxies=proxy_response) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    return path


def get_need_wall_post(wall_post: bool) -> int:
    if wall_post:
        return 1
    return 0

def wait_for_encoding(vk, video_id: int, owner_id: int, video_hash: str, proxy: dict, max_retries=20, delay: float = 3):
    for i in range(max_retries):
        try:
            resp = vk.shortVideo.encodeProgress(video_id=video_id, owner_id=owner_id, hash=video_hash)
        except vk_api.AuthError as e:
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


def upload_short_video(token: str, group_id: int, video_path: str, description: str, wall_post: bool, proxy: str):
    try:
        proxy_response = {
            "http": proxy,
            "https": proxy,
        }
        session = requests.Session()
        session.proxies.update({
            'http': proxy,
            'https': proxy
        })

        vk = vk_api.VkApi(token=token, session=session).get_api()
        file_size = os.path.getsize(video_path)
        # например, -12345 для паблика
        # 1. Получаем upload URL
        print("1. Получаем upload URL...")
        upload_data = vk.shortVideo.create(
            group_id=group_id,  # Обязательно
            file_size=file_size,  # Обязательно
        )

        # 2. Загружаем шортс
        print("2. Загружаем шортс...")
        with open(video_path, 'rb') as f:
            response = requests.post(upload_data['upload_url'], files={'file': f}, proxies=proxy_response)
        video_info = response.json()

        # 3. ВАЖНО: Добавляем задержку для обработки видео
        print("3. Ждем обработки шортс...")
        wait_for_encoding(vk, video_info['video_id'], video_info['owner_id'], video_info['video_hash'], proxy_response, 100, 3)

        # 3.5 Редактируем описание
        print("3.5 Редактируем описание...")
        edit_result = vk.shortVideo.edit(
            video_id=video_info['video_id'],  # Обязательно
            owner_id=video_info['owner_id'],  # Обязательно
            description=description,  # Текст описания
            privacy_view='all',
            can_make_duet=1
        )
        # print("Результат редактирования:")
        # print(json.dumps(edit_result, indent=2))

        # 4. Публикуем шортс
        print("4. Публикуем шортс...")
        need_wall_post = get_need_wall_post(wall_post)
        publish_result = vk.shortVideo.publish(
            video_id=video_info['video_id'],  # Обязательно
            owner_id=video_info['owner_id'],  # Обязательно
            license_agree=1,  # Обязательно
            publish_date=0,
            wallpost=need_wall_post,  # wallpost=0 если не нужно на стену
        )

        # print("\nОтвет метода shortVideo.publish:")
        # print(json.dumps(publish_result, indent=2))

        print("\nУСПЕХ! Шортс опубликован ✅")

        wall_post_id = None
        if 'video' in publish_result and 'wall_post_id' in publish_result['video']:
            wall_post_id = publish_result['video']['wall_post_id']
        elif 'wall_post_id' in publish_result:
            wall_post_id = publish_result['wall_post_id']

        #print(" ")
        print(f"Пост ID: {wall_post_id}")
        print(f"Ссылка: https://vk.com/wall-{group_id}_{wall_post_id}")

    except ApiError as e:
        print(f"\nОшибка VK API {e.code}: {e.error['error_msg']}")
        if e.code == 100:
            print("Ошибка VK API: Проверьте обязательные параметры:")
            raise e
        elif e.code == 3001:
            print("Ошибка VK API: Видео еще не обработано. Увеличьте время ожидания")
            raise e
        elif e.code == 9:
            print("Ошибка VK API 9: Flood control. Слишком много загрузок Shorts.")
            raise e
        else:
            raise
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {str(e)}")
        raise e


def delete_file(file_path: str) -> bool:
    """
    Удаляет файл по указанному пути.

    :param file_path: Путь к файлу
    :return: True, если файл успешно удалён, False — если файла нет
    """
    if not os.path.exists(file_path):
        print(f"⚠️ Файл не найден по пути: {file_path}")
        return False

    try:
        os.remove(file_path)
        print(f"✅ Файл '{file_path}' удалён.")
        return True
    except FileNotFoundError:
        print(f"⚠️ Файл '{file_path}' не найден.")
        return False
    except Exception as e:
        print(f"❌ Ошибка при удалении файла: {e}")
        return False
