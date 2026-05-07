from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class LiveLogAdd(BaseModel):
    user_id: int
    logtype: str
    log: str
    logdescription: Optional[str] = None

    model_config = ConfigDict(strict=False, extra="forbid")


class LiveLog(BaseModel):
    id: int
    user_id: int
    logtype: str
    log: str
    logdescription: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
