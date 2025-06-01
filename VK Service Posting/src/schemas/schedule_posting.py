from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SchedulePostingAdd(BaseModel):
    workpost_id: int
    clip_id: int
    task_id: str
    status: str

    model_config = ConfigDict(from_attributes=True)

class SchedulePosting(BaseModel):
    id: int
    workpost_id: int
    clip_id: int
    task_id: str
    status: str

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SchedulePostingUpdate(BaseModel):
    # все поля опциональные — можно обновлять любое подмножество
    clip_id: Optional[int] = None
    task_id: Optional[str] = None
    status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)