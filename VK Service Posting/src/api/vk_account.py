from collections import Counter

from fastapi import APIRouter, HTTPException, status, Body
from sqlalchemy import update

from src.api.dependencies import DataBaseDep, UserIdDep
from src.models.vk_group import VKGroupOrm
from src.schemas.vk_account import VKAccount, VKAccountAddCURL, VKAccountUpdate, DeleteVKAccountsLoginsRequest
from src.schemas.vk_account_cred import VKCredsRequestAdd, VKAccountCredRequestAutoCurlAdd
from src.services.auth import AuthService
from src.services.vk_account_backup import VKAccountBackupService
from src.services.vk_account_main import VKAccountMainService
from typing import List
from src.schemas.vk_account import VKAccountOut
from src.celery_app.tasks import vk_checker_add_account
from src.vk_api_methods.vk_account import get_vk_account_data
from src.vk_api_methods.vk_auth import get_new_token_request

router = APIRouter(prefix="/users/{user_id}/vk_accounts", tags=["VK Аккаунты"])


def _vk_accounts_with_decrypted_password(accounts: list[VKAccount]) -> list[VKAccount]:
    service_auth = AuthService()
    out: list[VKAccount] = []
    for acc in accounts:
        password = ""
        if acc.encrypted_password:
            password = service_auth.decrypt_data(acc.encrypted_password)
        out.append(acc.model_copy(update={"password": password}))
    return out


def _vk_accounts_with_posting_status(
        accounts: list[VKAccount],
        workerposts,
        groups,
        batch_label_by_id: dict | None = None,
) -> list[dict]:
    group_by_id = {group.id: group for group in groups}
    posting_by_account_id = {}
    batch_label_by_id = batch_label_by_id or {}

    # Выбираем наиболее релевантный workerpost на аккаунт:
    # приоритет у активного, иначе берём самый новый по id.
    for workerpost in workerposts:
        selected = posting_by_account_id.get(workerpost.vk_account_id)
        should_replace = (
            selected is None
            or (not selected.is_active and workerpost.is_active)
            or workerpost.id > selected.id
        )
        if should_replace:
            posting_by_account_id[workerpost.vk_account_id] = workerpost

    out: list[dict] = []
    for account in accounts:
        row = account.model_dump()
        batch_id = row.get("account_checker_batch_id")
        row["checker_batch_label"] = batch_label_by_id.get(batch_id) if batch_id else None

        workerpost = posting_by_account_id.get(account.id)

        if workerpost and workerpost.is_active:
            group = group_by_id.get(workerpost.vk_group_id)
            row.update({
                "posting_status": "posting",
                "workerpost_id": workerpost.id,
                "posting_public_url": group.vk_group_url if group else None,
                "posting_public_name": group.name if group else None,
            })
        else:
            row.update({
                "posting_status": "idle",
                "workerpost_id": workerpost.id if workerpost else None,
                "posting_public_url": None,
                "posting_public_name": None,
            })

        out.append(row)

    return out


def _build_v2_summary(
        accounts: list[VKAccount],
        proxy_count: int,
        workflow_count: int,
) -> dict:
    by_type = Counter(account.account_type or "unknown" for account in accounts)
    by_status = Counter(account.parse_status or "unknown" for account in accounts)
    recent_accounts = sorted(accounts, key=lambda account: account.id, reverse=True)[:6]

    return {
        "total_accounts": len(accounts),
        "with_proxy": sum(1 for account in accounts if account.proxy_id is not None),
        "with_cookies": sum(1 for account in accounts if account.cookies),
        "flooded": sum(1 for account in accounts if account.flood_control),
        "proxy_count": proxy_count,
        "workflow_count": workflow_count,
        "by_type": dict(by_type),
        "by_status": dict(by_status),
        "recent_accounts": [
            {
                "id": account.id,
                "vk_account_id": account.vk_account_id,
                "avatar_url": account.avatar_url,
                "name": account.name,
                "second_name": account.second_name,
                "login": account.login,
                "account_type": account.account_type,
                "parse_status": account.parse_status,
                "proxy_id": account.proxy_id,
                "cookies": account.cookies,
                "flood_control": account.flood_control,
                "vk_account_url": account.vk_account_url,
            }
            for account in recent_accounts
        ],
    }


@router.get("/all", summary="Получить все VK аккаунты пользователя")
async def get_all_vk_accounts(
        user_id: UserIdDep,
        database: DataBaseDep,
):
    """Возвращает все привязанные VK аккаунты пользователя"""
    accounts = await database.vk_account.get_all_filtered(user_id=user_id)
    return _vk_accounts_with_decrypted_password(accounts)


@router.get("/v2_summary", summary="Получить summary для V2 frontend")
async def get_vk_accounts_v2_summary(
        user_id: UserIdDep,
        database: DataBaseDep,
):
    accounts = await database.vk_account.get_all_filtered(user_id=user_id)
    proxies = await database.proxy.get_all_filtered(user_id=user_id)
    workerposts = await database.workerpost.get_all_filtered(user_id=user_id)

    return _build_v2_summary(
        accounts=accounts,
        proxy_count=len(proxies),
        workflow_count=len(workerposts),
    )

@router.get("/all_checker_connect", summary="Получить все VK аккаунты пользователя")
async def get_all_vk_accounts_checker_connect(
        user_id: UserIdDep,
        database: DataBaseDep,
):
    """Возвращает все привязанные VK аккаунты пользователя"""
    accounts = await database.vk_account.get_all_filtered(
        user_id=user_id,
        account_type=["checker", "connect"],
    )
    accounts = _vk_accounts_with_decrypted_password(accounts)
    account_ids = [account.id for account in accounts]

    if not account_ids:
        return []

    workerposts = await database.workerpost.get_all_filtered(
        user_id=user_id,
        vk_account_id=account_ids,
    )
    group_ids = list({workerpost.vk_group_id for workerpost in workerposts if workerpost.vk_group_id})
    groups = []
    if group_ids:
        groups = await database.vk_group.get_all_filtered(user_id=user_id, id=group_ids)

    batch_ids = {
        a.account_checker_batch_id
        for a in accounts
        if getattr(a, "account_checker_batch_id", None)
    }
    batch_label_by_id: dict = {}
    if batch_ids:
        batches = await database.account_checker_batch.get_all_filtered(
            user_id=user_id,
            id=list(batch_ids),
        )
        for b in batches:
            if b.id is not None and b.label:
                batch_label_by_id[b.id] = b.label

    return _vk_accounts_with_posting_status(accounts, workerposts, groups, batch_label_by_id)


@router.get("/vk_account_backup_count", summary="Получить кол-во Запасных VK аккаунтов")
async def get_all_vk_accounts_backup(
        user_id: UserIdDep,
        database: DataBaseDep,
):
    """Возвращает все привязанные VK аккаунты пользователя"""
    vk_accounts = await database.vk_account.get_all_filtered(account_type="backup", parse_status="success", flood_control=False, user_id=user_id)
    count = len(vk_accounts)
    return {"STATUS": "OK", "count": count}

@router.get("/vk_account_backup", summary="Получить все VK аккаунты пользователя Запасные")
async def get_all_vk_accounts_backup(
        user_id: UserIdDep,
        database: DataBaseDep,
):
    """Возвращает все привязанные VK аккаунты пользователя"""
    return await database.vk_account.get_all_filtered(account_type="backup", user_id=user_id)

@router.get("/vk_account_backup_out", response_model=List[VKAccountOut], summary="Получить все VK аккаунты пользователя Запасные вместе с Vk Cred")
async def get_all_vk_accounts_backup_out(
        user_id: UserIdDep,
        database: DataBaseDep,
):
    """Возвращает все привязанные VK аккаунты пользователя с кредами"""
    return await database.vk_account.get_all_backup_with_creds(user_id=user_id)

@router.get("/all_logins")
async def get_all_logins(database: DataBaseDep, user_id: UserIdDep,):
    all_accounts = await database.vk_account.get_all_filtered(account_type="backup", user_id=user_id)
    service_auth = AuthService()

    accounts = []
    for account in all_accounts:
        if account.login == "":
            accounts.append(f'curl vk id: {account.vk_account_id}')
            continue
        login = account.login
        password = service_auth.decrypt_data(account.encrypted_password)
        accounts.append(f"{login}:{password}")

    return {"accounts": accounts}

@router.get("/pending_logins")
async def get_pending_logins(database: DataBaseDep, user_id: UserIdDep,):
    all_accounts = await database.vk_account.get_all_filtered(parse_status="pending")
    service_auth = AuthService()

    accounts = []
    for account in all_accounts:
        if account.login == "":
            accounts.append(f'curl vk id: {account.vk_account_id}')
            continue
        login = account.login
        password = service_auth.decrypt_data(account.encrypted_password)
        accounts.append(f"{login}:{password}")

    return {"accounts": accounts}


@router.get("/blocked_logins")
async def get_blocked_logins(database: DataBaseDep, user_id: UserIdDep,):
    all_accounts = await database.vk_account.get_all_filtered(account_type="backup", flood_control=True, user_id=user_id)
    service_auth = AuthService()

    accounts = []
    for account in all_accounts:
        if account.login == "":
            accounts.append(f'curl vk id: {account.vk_account_id}')
            continue
        login = account.login
        password = service_auth.decrypt_data(account.encrypted_password)
        accounts.append(f"{login}:{password}")

    return {"accounts": accounts}

@router.get("/working_logins")
async def get_working_logins(database: DataBaseDep, user_id: UserIdDep,):
    all_accounts = await database.vk_account.get_all_filtered(account_type="backup", parse_status="success", flood_control=False, user_id=user_id)
    service_auth = AuthService()

    accounts = []
    for account in all_accounts:
        if account.login == "":
            accounts.append(f'curl vk id: {account.vk_account_id}')
            continue
        login = account.login
        password = service_auth.decrypt_data(account.encrypted_password)
        accounts.append(f"{login}:{password}")

    return {"accounts": accounts}


@router.get("/vk_account_poster", summary="Получить все VK аккаунты пользователя Постинг")
async def get_all_vk_accounts_poster(
        user_id: UserIdDep,
        database: DataBaseDep,
):
    """Возвращает все привязанные VK аккаунты пользователя"""
    return await database.vk_account.get_all_filtered(account_type="poster", user_id=user_id)


@router.get("/{vk_account_id}", summary="Получить конкретный VK аккаунт")
async def get_vk_account(
        user_id: UserIdDep,
        vk_account_id: int,
        database: DataBaseDep,
):
    """Возвращает детальную информацию о конкретном VK аккаунте"""
    account = await database.vk_account.get_one_or_none(
        id=vk_account_id,
        user_id=user_id
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VK аккаунт не найден"
        )

    return account

@router.get("/{vk_account_id}/status", summary="Статус парсинга VK аккаунта")
async def get_vk_account_status(
      user_id: UserIdDep,
      vk_account_id: int,
      database: DataBaseDep,
):
    account = await database.vk_account.get_one_or_none(id=vk_account_id)
    if not account:
        raise HTTPException(404, "Не найден VK аккаунт")
    return {
        "status": account.parse_status,   # pending | success | failure
        "task_id": account.task_id,
    }


@router.get("/{vk_account_id}/task_status", summary="Получить конкретный VK аккаунт статус")
async def get_vk_account_task_status(
        vk_account_id: int,
        database: DataBaseDep,
):
    return await VKAccountMainService(database).get_status(account_id=vk_account_id)


@router.post("/create_accounts", status_code=status.HTTP_201_CREATED, summary="Добавить сразу много аккаунтов Запасных по log:pass")
async def create_vk_accounts(
        user_id: UserIdDep,
        database: DataBaseDep,
        vk_creds: VKCredsRequestAdd,
):
    """Добавляет новый VK аккаунт для парсинга данных"""
    user = await database.user.get_one_or_none(id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )

    vk_creds = vk_creds.creds
    try:
        detail = await VKAccountBackupService(database).create_accounts(user_id, vk_creds)
        return {"status": "OK", "detail": detail}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/curl_main",
    status_code=status.HTTP_201_CREATED,
    summary="Добавить VK аккаунт по cURL(BASH) Главный технический"
)
async def create_vk_account_curl_main(
    user_id: UserIdDep,
    database: DataBaseDep,
    curl_command: VKAccountAddCURL,
):
    try:
        return await VKAccountMainService(database).create_account_curl(
            user_id=user_id,
            curl=curl_command.curl,
            account_type="main"
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post(
    "/curl_backup",
    status_code=status.HTTP_201_CREATED,
    summary="Добавить VK аккаунт по cURL(BASH) Запасной"
)
async def create_vk_account_curl_backup(
    user_id: UserIdDep,
    database: DataBaseDep,
    curl_command: VKAccountAddCURL,
):
    try:
        return await VKAccountBackupService(database).create_account_curl(
            user_id=user_id,
            curl=curl_command.curl,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/create_accounts_autocurl_backup", status_code=status.HTTP_201_CREATED, summary="Добавить сразу много аккаунтов Запасных по log:pass AutoCURL")
async def create_vk_accounts_autocurl_backup(
        user_id: UserIdDep,
        database: DataBaseDep,
        request_add: VKAccountCredRequestAutoCurlAdd,
):
    vk_creds_str = request_add.creds
    vk_groups_str = request_add.groups
    category_id_db = request_add.category_id
    try:
        detail = await VKAccountBackupService(database).create_vk_accounts_autocurl(user_id, vk_creds_str, vk_groups_str, category_id_db)
        return {"status": "OK", "detail": detail}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/retry", status_code=status.HTTP_204_NO_CONTENT, summary="Обновить данные аккаунта")
async def retry_vk_account(
    user_id: UserIdDep,
    database: DataBaseDep,
    current_user_id: UserIdDep,
):
    if current_user_id != user_id:
        raise HTTPException(status_code=403, detail="Нет доступа")

    return await VKAccountMainService(database).retry_account(user_id=user_id)


@router.post("/{vk_account_id}/check_curl", summary="Проверить, что cURL/токен аккаунта живой")
async def check_vk_account_curl(
    user_id: UserIdDep,
    vk_account_id: int,
    database: DataBaseDep,
):
    account = await database.vk_account.get_one_or_none(id=vk_account_id, user_id=user_id)
    if not account:
        raise HTTPException(status_code=404, detail="VK аккаунт не найден")

    proxy_http = None
    if account.proxy_id:
        proxy_db = await database.proxy.get_one_or_none(id=account.proxy_id)
        proxy_http = proxy_db.http if proxy_db else None

    token = get_new_token_request(account.token, account.cookies, proxy_http) or account.token
    if not token:
        return {"ok": False, "detail": "Не удалось получить токен"}

    try:
        get_vk_account_data(token, proxy_http)
    except Exception as e:
        return {"ok": False, "detail": f"Не удалось получить токен: {e}"}

    # Если web_token вернул новый — сохраняем его
    if token != account.token:
        await database.vk_account.edit(VKAccountUpdate(token=token), exclude_unset=True, id=account.id)
        await database.commit()

    return {"ok": True, "detail": "curl живой"}


@router.post("/{vk_account_id}/reconnect_curl", summary="Переподключить cURL через vk_login (log:pass)")
async def reconnect_vk_account_curl(
    user_id: UserIdDep,
    vk_account_id: int,
    database: DataBaseDep,
):
    account = await database.vk_account.get_one_or_none(id=vk_account_id, user_id=user_id)
    if not account:
        raise HTTPException(status_code=404, detail="VK аккаунт не найден")
    if not account.login or not account.encrypted_password:
        raise HTTPException(status_code=400, detail="Для переподключения нужен login:password аккаунта")

    password = AuthService().decrypt_data(account.encrypted_password)
    proxy_http = None
    if account.proxy_id:
        proxy_db = await database.proxy.get_one_or_none(id=account.proxy_id)
        proxy_http = proxy_db.http if proxy_db else None

    # backup — отдельный сценарий; checker / connect — флоу Account Checker, тип не понижать до backup
    target_account_type = "backup" if account.account_type == "backup" else "checker"

    task = vk_checker_add_account.delay(
        user_id,
        account.id,
        account.login,
        password,
        proxy_http,
        target_account_type,
    )
    await database.vk_account.edit(
        VKAccountUpdate(
            task_id=task.id,
            parse_status="pending",
            account_type=target_account_type,
        ),
        exclude_unset=True,
        id=account.id,
    )
    await database.commit()
    return {"status": "OK", "task_id": task.id}

@router.delete("/delete_list_logins", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить VK аккаунт по list логинам")
async def delete_vk_accounts_list_logins(
        user_id: UserIdDep,
        database: DataBaseDep,
        list_login: DeleteVKAccountsLoginsRequest = Body(...),
):
    logins = await VKAccountBackupService(database).delete_accounts(list_login.logins)
    return {"status": "OK", "deleted_logins": logins}

@router.delete("/{vk_account_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить VK аккаунт")
async def delete_vk_account(
        user_id: UserIdDep,
        vk_account_id: int,
        database: DataBaseDep,
):
    """Удаляет привязанный VK аккаунт и связанные данные"""
    await database.session.execute(
        update(VKGroupOrm)
        .where(VKGroupOrm.vk_admin_main_id == vk_account_id)
        .values(vk_admin_main_id=None)
    )
    await database.session.execute(
        update(VKGroupOrm)
        .where(VKGroupOrm.vk_admin_poster_id == vk_account_id)
        .values(vk_admin_poster_id=None)
    )

    celery_tasks_db = await database.celery_task.get_all_filtered(vk_account_id=vk_account_id)
    for task in celery_tasks_db:
        await database.celery_task.delete(id=task.id)

    await database.vk_account.delete(id=vk_account_id, user_id=user_id)
    await database.commit()

    return {"status": "OK"}