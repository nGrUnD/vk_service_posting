from pydantic import BaseModel, ConfigDict
from typing import Optional

class CeleryTaskAdd(BaseModel):
    task_id: str
    user_id: int
    vk_account_id: Optional[int] = None
    clip_list_id: Optional[int] = None
    vk_group_url: Optional[str] = None
    status: str
    type: Optional[str]

    model_config = ConfigDict(strict=False, extra="forbid")

class CeleryTask(BaseModel):
    id: int
    task_id: str
    user_id: int
    vk_account_id: Optional[int] = None
    clip_list_id: Optional[int] = None
    vk_group_url: Optional[str] = None
    status: Optional[str] = None
    type: Optional[str]

    model_config = ConfigDict(from_attributes=True)

class CeleryTaskUpdate(BaseModel):
    task_id: Optional[str] = None
    vk_account_id: Optional[int] = None
    clip_list_id: Optional[int] = None
    vk_group_url: Optional[str] = None
    status: Optional[str] = None
    type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)