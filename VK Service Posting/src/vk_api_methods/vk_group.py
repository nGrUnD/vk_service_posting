import requests
from src.utils.rand_user_agent import get_random_user_agent


def _build_session(proxy: str | None) -> requests.Session:
    session = requests.Session()
    if proxy is None:
        session.trust_env = False
    else:
        session.proxies.update({
            "http": proxy,
            "https": proxy,
        })
    return session


def join_group(group_id: int, access_token: str, proxy: str):
    url = "https://api.vk.ru/method/groups.join"
    params = {
        "group_id": group_id,
        "access_token": access_token,
        "v": "5.131"
    }
    print(f'proxy: {proxy}')
    headers = {"User-Agent": get_random_user_agent()}
    session = _build_session(proxy)
    response = session.post(url, data=params, headers=headers)
    result = response.json()
    if "error" in result:
        print(f"Ошибка: {result['error']['error_msg']}")
        return False

    print("Успешно вступили в группу.")
    return True

def assign_editor_role(group_id: int, user_id: int, access_token: str, proxy: str = None):
    url = "https://api.vk.ru/method/groups.editManager"
    params = {
        "group_id": group_id,
        "user_id": user_id,
        "role": "editor",
        "access_token": access_token,
        "v": "5.275"
    }
    session = _build_session(proxy)
    response = session.post(url, data=params)
    result = response.json()
    if "error" in result:
        print(f"Ошибка: {result['error']['error_msg']}")
        return False
        #print(f"Ошибка: {result['error']['error_msg']}")

    print("Роль редактора успешно назначена.")
    return True