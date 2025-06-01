from typing import Optional

from pydantic import BaseModel, ConfigDict

class CategoryAddRequest(BaseModel):
    clip_list_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    repost_enabled: bool = False
    daily_limit: int = 0
    hourly_limit: int = 0
    is_active: bool = False

class CategoryAdd(BaseModel):
    user_id: int
    clip_list_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    repost_enabled: bool = False
    daily_limit: int = 0
    hourly_limit: int = 0
    is_active: bool = False

class Category(BaseModel):
    user_id: int
    clip_list_id: Optional[int] = None
    id: int
    name: str
    description: Optional[str] = None
    repost_enabled: bool = False
    daily_limit: int = 0
    hourly_limit: int = 0
    is_active: bool = False

    model_config = ConfigDict(from_attributes=True)


class CategoryUpdate(BaseModel):
    clip_list_id: Optional[int]
    name: Optional[str]
    description: Optional[str]
    repost_enabled: Optional[bool]
    daily_limit: Optional[int]
    hourly_limit: Optional[int]
    is_active: Optional[bool]

    model_config = ConfigDict(from_attributes=True)