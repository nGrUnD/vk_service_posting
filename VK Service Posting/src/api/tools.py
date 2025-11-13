from fastapi import APIRouter
from src.api.dependencies import DataBaseDep, UserIdDep
from src.schemas.tools import AccountCheckResponse, AccountInput, AccountChangeResponse
from src.services.vk_account_checker import AccountChecker

router = APIRouter(prefix="/tools/{user_id}", tags=["Tools"])

# ==== Эндпоинт проверки аккаунтов ====
@router.post("/account_checker")
async def account_checker(data: AccountInput, database: DataBaseDep, user_id: UserIdDep,):
    service_checker = AccountChecker(database)
    results = await service_checker.add_account(data, user_id)

    return {"status": "OK", "detail": results}


# ==== Эндпоинт смены паролей ====
@router.post("/account_change_passwords", response_model=AccountChangeResponse)
async def change_passwords(data: AccountInput, database: DataBaseDep, user_id: UserIdDep,):
    service_checker = AccountChecker(database)
    results = await service_checker.change_password(data, user_id)

    return AccountChangeResponse(new_accounts=results)