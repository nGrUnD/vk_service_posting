import requests
from src.utils.rand_user_agent import get_random_user_agent


def join_group(group_id: int, access_token: str, proxy: str):
    url = "https://api.vk.com/method/groups.join"
    params = {
        "group_id": group_id,
        "access_token": access_token,
        "v": "5.131"
    }
    proxy_response = None
    if proxy is not None:
        proxy_response = {
            "http": proxy,
            "https": proxy,
        }

    print(proxy)
    headers = {"User-Agent": get_random_user_agent()}

    response = requests.post(url, data=params, headers=headers, proxies=proxy_response)
    result = response.json()
    if "error" in result:
        print(f"Ошибка: {result['error']['error_msg']}")
        return False

    print("Успешно вступили в группу.")
    return True

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
        return False
        #print(f"Ошибка: {result['error']['error_msg']}")

    print("Роль редактора успешно назначена.")
    return True