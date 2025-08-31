from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List

class VKAccountGroupBase(BaseModel):
    vk_account_id: int
    vk_group_id: int
    role: str  # 'main', 'poster'


class VKAccountGroup(VKAccountGroupBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class VKAccountGroupUpdate(BaseModel):
    role: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
