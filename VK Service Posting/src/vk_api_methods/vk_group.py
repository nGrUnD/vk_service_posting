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


def _is_already_in_group_error(error: dict) -> bool:
    msg = (error.get("error_msg") or "").lower()
    # «уже», дубликат вступления, типичные формулировки VK
    if any(
        s in msg
        for s in (
            "уже",
            "already",
            "подпис",
            "member",
            "участник",
            "в сообществе",
        )
    ):
        return True
    return False


def is_group_member(group_id: int, access_token: str, proxy: str | None) -> bool:
    """Проверка, что владелец access_token состоит в группе (0/1)."""
    url = "https://api.vk.ru/method/groups.isMember"
    params = {
        "group_id": group_id,
        "access_token": access_token,
        "v": "5.131",
    }
    headers = {"User-Agent": get_random_user_agent()}
    session = _build_session(proxy)
    response = session.get(url, params=params, headers=headers)
    result = response.json()
    if "error" in result:
        print(f"Ошибка isMember: {result['error']}")
        return False
    resp = result.get("response")
    if isinstance(resp, int):
        return resp == 1
    if isinstance(resp, dict):
        return int(resp.get("member", 0)) == 1
    return False


def join_group(group_id: int, access_token: str, proxy: str | None = None) -> bool:
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
        err = result["error"]
        if _is_already_in_group_error(err):
            print("Пользователь уже в группе (groups.join).")
            return True
        print(f"Ошибка: {err.get('error_msg', err)}")
        return False

    print("Успешно вступили в группу.")
    return True


def ensure_user_in_club_for_editor(
    group_id: int, backup_account_token: str, proxy: str | None
) -> bool:
    """
    Перед groups.editManager пользователь (backup) должен состоять в сообществе.
    Ранее join вызывали только при отсутствии encrypted_curl, из‑за чего
    follow-up autocurl с curl пропускал вступление и ловил «User should be in club».
    """
    if is_group_member(group_id, backup_account_token, proxy):
        print("Пользователь уже в группе (isMember).")
        return True
    if join_group(group_id, backup_account_token, proxy):
        return True
    # join мог вернуть false при гонке — перепроверяем
    if is_group_member(group_id, backup_account_token, proxy):
        return True
    return False

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