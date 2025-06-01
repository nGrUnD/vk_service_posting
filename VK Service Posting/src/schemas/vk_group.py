from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

class VKGroupRequestAddUrl(BaseModel):
    vk_links: list[str]
    min_views: int
    parse_all: bool
    date_range: Optional[datetime] = None
    clip_list_id: int

class VKGroupAdd(BaseModel):
    user_id: int
    vk_group_id: Optional[int] = None
    vk_admin_main_id: Optional[int] = None
    vk_admin_poster_id : Optional[int] = None
    vk_group_type: str # source | poster | main
    vk_group_url: str
    avatar_url: str
    name: str
    clips_count: int = 0
    parse_status: str
    task_id: str

class VKGroup(BaseModel):
    id: int
    user_id: int
    vk_group_id: Optional[int] = None
    vk_admin_main_id: Optional[int] = None
    vk_admin_poster_id : Optional[int] = None
    vk_group_type: str # source | poster | main
    vk_group_url: str
    avatar_url: str
    name: str
    clips_count: int = 0
    parse_status: str
    task_id: str

    model_config = ConfigDict(from_attributes=True)

class VKGroupUpdate(BaseModel):
    # все поля опциональные — можно обновлять любое подмножество
    vk_group_id: Optional[int] = None
    vk_admin_main_id: Optional[int] = None
    vk_admin_poster_id: Optional[int] = None
    vk_group_type: Optional[str] = None # source | poster | main
    vk_group_url: Optional[str] = None
    avatar_url: Optional[str] = None
    name: Optional[str] = None
    clips_count: Optional[int] = None
    parse_status: Optional[str] = None
    task_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
