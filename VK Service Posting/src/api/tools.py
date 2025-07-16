from fastapi import APIRouter
from src.api.dependencies import DataBaseDep
from src.schemas.tools import AccountCheckResponse, AccountInput, AccountChangeResponse
from src.services.vk_account_checker import AccountChecker

router = APIRouter(prefix="/tools", tags=["Tools"])

# ==== Эндпоинт проверки аккаунтов ====
@router.post("/account_checker", response_model=AccountCheckResponse)
async def account_checker(data: AccountInput, database: DataBaseDep,):
    service_checker = AccountChecker(database)
    results = await service_checker.check(data)

    return AccountCheckResponse(results=results)


# ==== Эндпоинт смены паролей ====
@router.post("/account_change_passwords", response_model=AccountChangeResponse)
async def change_passwords(data: AccountInput, database: DataBaseDep,):
    service_checker = AccountChecker(database)
    results = await service_checker.change_password(data)

    return AccountChangeResponse(new_accounts=results)
