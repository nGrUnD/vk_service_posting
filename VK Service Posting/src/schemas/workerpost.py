from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from src.schemas.category import Category
from src.schemas.vk_account import VKAccount
from src.schemas.vk_group import VKGroup


class WorkerPostRequestAdd(BaseModel):
    #creds: str
    vk_groups_links: list[str]
    category_id: int


class WorkerPostAdd(BaseModel):
    user_id: int
    vk_group_id: int
    vk_account_id: int
    category_id: int

    is_active: bool
    banner_video_path: Optional[str] = None
    banner_x: Optional[float] = None
    banner_y: Optional[float] = None
    banner_width: Optional[float] = None
    banner_height: Optional[float] = None
    banner_remove_green_background: bool = True
    last_post_at: Optional[datetime] = None

    model_config = ConfigDict(strict=False, extra="forbid")


class WorkerPost(BaseModel):
    id: int
    user_id: int
    vk_group_id: int
    vk_account_id: int
    category_id: int

    is_active: bool
    banner_video_path: Optional[str]
    banner_x: Optional[float]
    banner_y: Optional[float]
    banner_width: Optional[float]
    banner_height: Optional[float]
    banner_remove_green_background: bool
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
    is_active: Optional[bool] = None
    banner_video_path: Optional[str] = None
    banner_x: Optional[float] = None
    banner_y: Optional[float] = None
    banner_width: Optional[float] = None
    banner_height: Optional[float] = None
    banner_remove_green_background: Optional[bool] = None
    last_post_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
