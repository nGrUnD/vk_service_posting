from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class VKClipAdd(BaseModel):
    user_id: int
    clip_list_id: int
    vk_group_id: int

    vk_id: int
    files: str
    views: int
    date: datetime
    frames_file: str

    parse_status: str
    task_id: str

class VKClipOut(BaseModel):
    id: int
    user_id: int
    clip_list_id: int
    vk_group_id: int

    vk_id: int
    files: str
    views: int
    date: datetime
    frames_file: str

    parse_status: str
    task_id: str

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VKClip(BaseModel):
    id: int
    user_id: int
    clip_list_id: int
    vk_group_id: int

    vk_id: int
    files: str
    views: int
    date: datetime
    frames_file: str

    parse_status: Optional[str]
    task_id: Optional[str]

    model_config = ConfigDict(from_attributes=True)

class VKClipUpdate(BaseModel):
    vk_id: Optional[int]
    files: Optional[str]
    views: Optional[int]
    date: Optional[datetime]
    frames_file: Optional[str]

    parse_status: Optional[str]
    task_id: Optional[str]


    model_config = ConfigDict(from_attributes=True)