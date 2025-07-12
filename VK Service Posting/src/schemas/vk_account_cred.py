from pydantic import BaseModel, ConfigDict
from datetime import datetime

class VKCredsRequestAdd(BaseModel):
    creds: str

class VKAccountCredRequestAdd(BaseModel):
    login: str
    password: str


class VKAccountCredAdd(BaseModel):
    user_id: int
    login: str
    encrypted_password: str

class VKAccountCredOut(BaseModel):
    id: int
    login: str
    encrypted_password: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VKAccountCred(BaseModel):
    user_id: int
    id: int
    login: str
    encrypted_password: str

    model_config = ConfigDict(from_attributes=True)