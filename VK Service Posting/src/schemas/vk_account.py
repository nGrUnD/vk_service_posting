from typing import Optional
import enum
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AccountType(str, enum.Enum):
    MAIN = "main"        # технический главный аккаунт
    POSTER = "poster"    # аккаунт, который постит клипы
    PARSER = "backup"    # запасной аккаунт для парсинга

class DeleteVKAccountsLoginsRequest(BaseModel):
    logins: list[str]


class VKAccountAddCURL(BaseModel):
    curl: str

class VKAccountAdd(BaseModel):
    user_id: int
    proxy_id: Optional[int] = None
    vk_account_id: int
    encrypted_curl: str
    login: str
    encrypted_password: str
    vk_account_url : str
    avatar_url: str
    name: str
    second_name: str
    groups_count: int = 0
    flood_control: bool = False
    parse_status: str
    task_id: str
    account_type: str   # новое поле

class VKAccountOut(BaseModel):
    id: int
    vk_account_id: int
    user_id: int
    encrypted_curl: str
    login: str
    encrypted_password: str
    account_type: str
    vk_account_url: str
    avatar_url: str
    name: str
    second_name: str
    groups_count: int
    flood_control: bool
    parse_status: str
    task_id: str
    created_at: datetime
    updated_at: datetime


    model_config = ConfigDict(from_attributes=True)


class VKAccount(BaseModel):
    id: int
    vk_account_id: int
    user_id: int
    encrypted_curl: str
    login: str
    encrypted_password: str
    proxy_id: Optional[int] = None
    vk_account_url : str
    avatar_url: str
    name: str
    second_name: str
    groups_count: int
    flood_control: bool = False
    parse_status: str
    task_id: str
    account_type: str

    model_config = ConfigDict(from_attributes=True)


class VKAccountUpdate(BaseModel):
    # все поля опциональные — можно обновлять любое подмножество
    proxy_id: Optional[int] = None
    vk_account_id: Optional[int] = None
    avatar_url: Optional[str] = None
    vk_account_url: Optional[str] = None
    name: Optional[str] = None
    second_name: Optional[str] = None
    groups_count: Optional[int] = None
    flood_control: Optional[bool] = None
    parse_status: Optional[str] = None
    task_id: Optional[str] = None
    encrypted_curl: Optional[str] = None
    login: Optional[str] = None
    encrypted_password: Optional[str] = None
    account_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
