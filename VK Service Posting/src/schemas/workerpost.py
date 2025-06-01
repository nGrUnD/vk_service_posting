from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from src.schemas.category import Category
from src.schemas.vk_account import VKAccount
from src.schemas.vk_group import VKGroup


class WorkerPostRequestAdd(BaseModel):
    creds: str
    vk_groups_links: list[str]
    category_id: int


class WorkerPostAdd(BaseModel):
    user_id: int
    vk_group_id: int
    vk_account_id: int
    category_id: int

    is_active: bool
    last_post_at: Optional[datetime] = None

    model_config = ConfigDict(strict=False, extra="forbid")


class WorkerPost(BaseModel):
    id: int
    user_id: int
    vk_group_id: int
    vk_account_id: int
    category_id: int

    is_active: bool
    last_post_at: Optional[datetime]

    #vk_group: VKGroup
    #vk_account: VKAccount
    #category: Category

    model_config = ConfigDict(from_attributes=True)


class WorkerPostUpdate(BaseModel):
    # все поля опциональные — можно обновлять любое подмножество
    vk_group_id: Optional[int] = None
    vk_account_id: Optional[int] = None
    category_id: Optional[int] = None
    is_active: Optional[bool]
    last_post_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
