from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

from src.schemas.category import Category
from src.schemas.vk_account import VKAccount
from src.schemas.vk_group import VKGroup


class WorkerPostRequestAdd(BaseModel):
    #creds: str
    vk_groups_links: list[str]
    category_id: int


class WorkerPostPreviewLinkRow(BaseModel):
    link: str
    vk_public_id: Optional[int] = None
    status: Literal[
        "will_queue",
        "invalid_url",
        "missing_group",
        "no_backup",
        "no_category",
        "no_main",
        "already_workerpost",
    ]
    detail: Optional[str] = None
    chosen_account_id: Optional[int] = None


class WorkerPostPreviewResponse(BaseModel):
    links: list[WorkerPostPreviewLinkRow]
    will_queue: int = 0
    will_fail: int = 0
    missing_group_in_admin: int = 0
    no_backup_linked: int = 0
    invalid_url: int = 0
    no_main_account: bool = False
    no_category: bool = False
    already_workerpost: int = 0


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
