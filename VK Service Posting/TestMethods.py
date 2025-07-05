import requests

import src.services.vk_token_service
from vkapi.methods import get_all_owner_short_videos, get_owner_short_videos_page, download_vk_clip, upload_short_video, \
    get_owner_short_videos, get_vk_access_token_from_file, get_vk_access_token_from_curl, get_curl_from_file, \
    get_access_token_vk, get_vk_session_by_log_pass, vk_api_get_owner_short_videos, download_clip_by_url
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from vkapi.vkauth import get_vk_account_curl_from_browser
from src.vk_api.vk_account import get_vk_account_admin_groups as get_vk_account_group_data


def read_token_from_file(path: str = 'vktoken.txt') -> str:
    """
    Читает access_token из указанного текстового файла.
    """
    with open(path, 'r', encoding='utf-8') as f:            # Открываем файл на чтение :contentReference[oaicite:0]{index=0}
        token = f.read().strip()                            # Считываем и обрезаем пробельные символы
    return token


def read_vk_accounts(file_path: str = 'vkaccount.txt') -> list[tuple[str, str]]:
    """
    Читает файл с учётками VK, каждая строка в формате login:password.

    :param file_path: путь к файлу vkaccount.txt
    :return: список кортежей (login, password)
    """
    accounts = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Убираем пробельные символы по краям (включая '\n')
            line = line.strip()
            # Пропускаем пустые строки
            if not line:
                continue
            # Разбиваем по первому вхождению двоеточия
            if ':' in line:
                login, password = line.split(':', 1)
                accounts.append((login, password))
            else:
                # Если формат не тот — можно выкинуть предупреждение или ошибку
                raise ValueError(f"Неправильный формат строки: {line!r}")
    return accounts


def get_single_vk_account(file_path: str = 'vkaccount.txt', index: int = 0) -> tuple[str, str]:
    """
    Возвращает кортеж (login, password) для одной учётки из файла vkaccount.txt.
    По умолчанию берёт аккаунт с указанным индексом (0 — первый).
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        # Считаем все строки и сразу очистим их от лишнего
        lines = [line.strip() for line in f if line.strip()]
    try:
        line = lines[index]
    except IndexError:
        raise IndexError(f"No account at index {index}; file contains only {len(lines)} entries.")

    if ':' not in line:
        raise ValueError(f"Неправильный формат: {line!r}. Ожидается 'login:password'.")

    login, password = line.split(':', 1)
    return login, password

def get_vk_account_data(access_token: str):
    # URL для запроса данных аккаунта
    url = "https://api.vk.com/method/users.get"

    # Параметры запроса
    params = {
        "access_token": access_token,
        "v": "5.131",  # Версия API
        "fields": "photo_200"  # Поля, которые нужно получить
    }

    # Отправка запроса
    response = requests.get(url, params=params)
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

def get_vk_account_admin_groups(access_token: str, user_id: int):
    # URL для запроса данных аккаунта
    url = "https://api.vk.com/method/groups.get"

    # Параметры запроса
    params = {
        "access_token": access_token,
        "v": "5.131",  # Версия API
        "user_id": user_id,
        "filter": "admin",
        #"fields": "photo_200"  # Поля, которые нужно получить
    }

    # Отправка запроса
    response = requests.get(url, params=params)
    data = response.json()['response']

    # Проверка на ошибки
    if "error" in data:
        raise Exception(f"Ошибка при получении данных: {data['error']['error_msg']}")

    # Извлечение данных
    print(data)
    count = data["count"]

    return {
        "count": count
    }

def vk_api_get_clip_from_group(vk_session, owner_id: int):
    data = vk_api_get_owner_short_videos(owner_id, vk_session)
    clip_data = data['items'][0]
    print(f"group data: {data['groups']}")
    print(f"date: {clip_data["date"]}")
    print(f"views: {clip_data["views"]}")
    print(f"id: {clip_data["id"]}")
    print(f"timeline_thumbs links: {clip_data["timeline_thumbs"]["links"]}")
    clip_files = clip_data['files']

    vk_clip_url = f"https://vk.com/video{owner_id}_{clip_data['id']}"
    saved = download_clip_by_url(vk_clip_url)
    print(f"Видео сохранено в: {saved}")
    return saved, clip_files


def get_clip_from_group(access_token: str, owner_id: int):
    data = get_owner_short_videos(owner_id, access_token)
    clip_data = data['items'][0]
    print(f"group data: {data['groups']}")
    print(f"date: {clip_data["date"]}")
    print(f"views: {clip_data["views"]}")
    print(f"id: {clip_data["id"]}")
    print(f"timeline_thumbs links: {clip_data["timeline_thumbs"]["links"]}")
    clip_files = clip_data['files']
    saved = download_vk_clip(clip_files)
    print(f"Видео сохранено в: {saved}")
    return clip_files


def join_group(group_id: int, access_token: str):
    url = "https://api.vk.com/method/groups.join"
    params = {
        "group_id": group_id,
        "access_token": access_token,
        "v": "5.131"
    }
    response = requests.post(url, data=params)
    result = response.json()
    if "error" in result:
        print(f"Ошибка: {result['error']['error_msg']}")
    else:
        print("Успешно вступили в группу.")

def assign_editor_role(group_id: int, user_id: int, access_token: str):
    url = "https://api.vk.com/method/groups.editManager"
    params = {
        "group_id": group_id,
        "user_id": user_id,
        "role": "editor",
        "access_token": access_token,
        "v": "5.131"
    }
    response = requests.post(url, data=params)
    result = response.json()
    if "error" in result:
        print(f"Ошибка: {result['error']['error_msg']}")
    else:
        print("Роль редактора успешно назначена.")


def get_clips_from_group(token = ""):
    # Пример параметров из вашего вопроса
    owner_id = -226882140
    owner_id_download_clip = -223170164
    count = 1
    #access_token = read_token_from_file()
    #login, pswd = get_single_vk_account()
    #curl = get_vk_account_curl_from_browser(login, pswd)
    #print(f"curl:")
    #print(curl)

    #if token != "":
    #access_token = token
    #access_token = get_vk_access_token_from_file()
    #access_token = get_vk_access_token_from_curl(curl)
    #print(f"access token: {access_token}")
    #access_token = get_vk_access_token_from_file("curl.txt")
    user_id = 1037099911
    curl = get_curl_from_file()

    with open("file.txt", "r", encoding="utf-8") as f:
        line = f.readline().strip()  # читаем первую строку и убираем \n
        login, password = line.split(":")

    vk_session = get_vk_session_by_log_pass(login, password)
    token_data = vk_session.token
    print(token_data['access_token'])
    session_token = token_data['access_token']
    #access_token = get_access_token_vk(session_token)
    #print(access_token)
    access_token = src.services.vk_token_service.TokenService.get_token_from_curl(curl)

    vk_data = get_vk_account_data(session_token)
    print(f"vk data: {vk_data}")

    #vk_groups_data = get_vk_account_group_data(access_token, vk_data['id'])
    #print(f"vk_groups_data: {vk_groups_data}")

    saved, clip_files = vk_api_get_clip_from_group(vk_session, owner_id_download_clip)

    #clips = get_all_owner_short_videos(owner_id_download_clip, access_token, max_count=50)
    #print(f"clips: {len(clips)}")

    #saved = download_vk_clip(clip_files)
    #join_group(owner_id_2, access_token)
    #assign_editor_role(owner_id_2, user_id, access_token2)
    #print(clips)

    upload_short_video(access_token, owner_id*-1, saved)

    #data = get_all_owner_short_videos(owner_id, access_token)
    #print(data)
    #date_value = data['response']['items'][0]['date']
    #print("Timestamp:", date_value)


def main():
    #login, pwd = get_single_vk_account()
    #token = run_vk_browser(login, pwd)
    #print(token)
    get_clips_from_group()

if __name__ == '__main__':
    main()