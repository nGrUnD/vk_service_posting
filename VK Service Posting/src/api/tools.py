from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from src.api.dependencies import DataBaseDep, UserIdDep
from src.schemas.account_checker_batch import AccountCheckerBatchStatusOut
from src.schemas.tools import AccountCheckerSubmitResponse, AccountInput, AccountChangeResponse
from src.services.vk_account_checker import AccountChecker

router = APIRouter(prefix="/tools/{user_id}", tags=["Tools"])


def _account_checker_status_payload(batch) -> AccountCheckerBatchStatusOut:
    now = datetime.now(timezone.utc)
    created = batch.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    end = batch.completed_at or now
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    elapsed = max(0.0, (end - created).total_seconds())
    duration: float | None = None
    if batch.status == "completed" and batch.completed_at is not None:
        c = batch.completed_at
        if c.tzinfo is None:
            c = c.replace(tzinfo=timezone.utc)
        duration = max(0.0, (c - created).total_seconds())
    return AccountCheckerBatchStatusOut(
        batch_id=batch.id,
        user_id=batch.user_id,
        status=batch.status,
        total_tasks=batch.total_tasks,
        completed_tasks=batch.completed_tasks,
        created_at=batch.created_at,
        completed_at=batch.completed_at,
        duration_seconds=duration,
        elapsed_seconds=elapsed,
    )


# ==== Эндпоинт проверки аккаунтов ====
@router.post("/account_checker", response_model=AccountCheckerSubmitResponse)
async def account_checker(
    data: AccountInput,
    database: DataBaseDep,
    user_id: UserIdDep,
):
    service_checker = AccountChecker(database)
    results = await service_checker.add_account(data, user_id)
    if isinstance(results, dict):
        return {
            "status": "OK",
            "detail": str(results.get("detail", "ALL OK")),
            "batch_id": results.get("batch_id"),
            "queued": int(results.get("queued", 0)),
        }
    return {
        "status": "OK",
        "detail": str(results) if results is not None else "ALL OK",
        "batch_id": None,
        "queued": 0,
    }


@router.get(
    "/account_checker/batch/{batch_id}",
    response_model=AccountCheckerBatchStatusOut,
    summary="Статус батча: время от приёма до завершения фоновой обработки",
)
async def get_account_checker_batch(
    batch_id: int,
    database: DataBaseDep,
    user_id: UserIdDep,
):
    batch = await database.account_checker_batch.get_one_or_none(
        id=batch_id,
        user_id=user_id,
    )
    if not batch:
        raise HTTPException(status_code=404, detail="Батч не найден")
    return _account_checker_status_payload(batch)


# ==== Эндпоинт смены паролей ====
@router.post("/account_change_passwords", response_model=AccountChangeResponse)
async def change_passwords(data: AccountInput, database: DataBaseDep, user_id: UserIdDep,):
    service_checker = AccountChecker(database)
    results = await service_checker.change_password(data, user_id)

    return AccountChangeResponse(new_accounts=results)