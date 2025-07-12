from fastapi import APIRouter, HTTPException, status, Body

from src.api.dependencies import DataBaseDep, UserIdDep
from src.schemas.vk_account import VKAccountAddCURL, DeleteVKAccountsLoginsRequest
from src.schemas.vk_account_cred import VKCredsRequestAdd
from src.services.auth import AuthService
from src.services.vk_account_backup import VKAccountBackupService
from src.services.vk_account_main import VKAccountMainService
from typing import List
from src.schemas.vk_account import VKAccountOut

router = APIRouter(prefix="/users/{user_id}/vk_accounts", tags=["VK Аккаунты"])


@router.get("/all", summary="Получить все VK аккаунты пользователя")
async def get_all_vk_accounts(
        user_id: UserIdDep,
        database: DataBaseDep,
):
    """Возвращает все привязанные VK аккаунты пользователя"""
    return await database.vk_account.get_all_filtered(user_id=user_id)

@router.get("/vk_account_backup_count", summary="Получить кол-во Запасных VK аккаунтов")
async def get_all_vk_accounts_backup(
        user_id: UserIdDep,
        database: DataBaseDep,
):
    """Возвращает все привязанные VK аккаунты пользователя"""
    vk_accounts = await database.vk_account.get_all_filtered(account_type="backup", flood_control=False, user_id=user_id)
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
        account_cred = await database.vk_account_cred.get_one_or_none(id=account.vk_cred_id)
        if not account_cred:
            continue

        login = account_cred.login
        password = service_auth.decrypt_data(account_cred.encrypted_password)
        accounts.append(f"{login}:{password}")

    return {"accounts": accounts}

@router.get("/blocked_logins")
async def get_blocked_logins(database: DataBaseDep, user_id: UserIdDep,):
    all_accounts = await database.vk_account.get_all_filtered(account_type="backup", flood_control=True, user_id=user_id)
    service_auth = AuthService()

    accounts = []
    for account in all_accounts:
        account_cred = await database.vk_account_cred.get_one_or_none(id=account.vk_cred_id)
        if not account_cred:
            continue

        login = account_cred.login
        password = service_auth.decrypt_data(account_cred.encrypted_password)
        accounts.append(f"{login}:{password}")

    return {"accounts": accounts}

@router.get("/working_logins")
async def get_working_logins(database: DataBaseDep, user_id: UserIdDep,):
    all_accounts = await database.vk_account.get_all_filtered(account_type="backup", flood_control=False, user_id=user_id)
    service_auth = AuthService()

    accounts = []
    for account in all_accounts:
        account_cred = await database.vk_account_cred.get_one_or_none(id=account.vk_cred_id)
        if not account_cred:
            continue

        login = account_cred.login
        password = service_auth.decrypt_data(account_cred.encrypted_password)
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


@router.post("", status_code=status.HTTP_201_CREATED, summary="Добавить новый VK аккаунт")
async def create_vk_account(
        user_id: UserIdDep,
        vk_cred_id: int,
        database: DataBaseDep,
):
    """Добавляет новый VK аккаунт для парсинга данных"""
    try:
        return await VKAccountMainService(database).create_account(user_id=user_id, vk_cred_id=vk_cred_id)
        # return await database.vk_account.create_account(user_id=user_id, vk_cred_id=data.vk_cred_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

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
        # return await database.vk_account.create_account(user_id=user_id, vk_cred_id=data.vk_cred_id)
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
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/{account_id}/retry", status_code=status.HTTP_204_NO_CONTENT, summary="Обновить данные аккаунта")
async def retry_vk_account(
    user_id: UserIdDep,
    account_id: int,
    database: DataBaseDep,
    current_user_id: UserIdDep,
):
    if current_user_id != user_id:
        raise HTTPException(status_code=403, detail="Нет доступа")

    return await VKAccountMainService(database).retry_account(user_id=user_id, vk_account_id=account_id)

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
    await database.vk_account.delete(id=vk_account_id, user_id=user_id)
    await database.commit()

    return {"status": "OK"}