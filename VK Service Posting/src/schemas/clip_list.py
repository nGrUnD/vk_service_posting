from typing import Optional, List

from pydantic import BaseModel, ConfigDict

from src.schemas.vk_clip import VKClipOut


class ClipListAddRequest(BaseModel):
    name: str

class ClipListAdd(BaseModel):
    user_id: int
    name: str
    parse_status: str
    task_id: str

class ClipList(BaseModel):
    id: int
    user_id: int
    name: str
    parse_status: str
    task_id: str

    clips: List[VKClipOut] = []  # Список вложенных объектов VKClipOut

    model_config = ConfigDict(from_attributes=True)


class ClipListUpdate(BaseModel):
    name: Optional[str]
    parse_status: Optional[str]
    task_id: Optional[str]

    model_config = ConfigDict(from_attributes=True)