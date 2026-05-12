from typing import List, Literal, Optional

from pydantic import BaseModel

# ==== Модели ====
class AccountInput(BaseModel):
    accounts: List[str]
    batch_label: Optional[str] = None

class AccountCheckResult(BaseModel):
    login: str
    password: str
    status: Literal["Work", "Blocked", "FloodControl", "NotExists", "Error"]

class AccountCheckResponse(BaseModel):
    results: List[AccountCheckResult]


class AccountCheckerSubmitResponse(BaseModel):
    status: str
    detail: str
    batch_id: Optional[int] = None
    queued: int = 0

class AccountChangeResult(BaseModel):
    login: str
    password: str

class AccountChangeResponse(BaseModel):
    new_accounts: List[AccountChangeResult]


class ChangePasswordByIdItem(BaseModel):
    vk_account_id: int
    ok: bool
    login: Optional[str] = None
    detail: Optional[str] = None


class ChangePasswordsByIdsResponse(BaseModel):
    results: List[ChangePasswordByIdItem]
