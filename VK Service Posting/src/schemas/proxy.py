from pydantic import BaseModel, ConfigDict
from datetime import datetime

class ProxyRequestAdd(BaseModel):
    proxys: str

class ProxyRequestDelete(BaseModel):
    proxys: list[str]

class ProxyAdd(BaseModel):
    user_id: int
    http: str

class ProxyOut(BaseModel):
    id: int
    http: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Proxy(BaseModel):
    user_id: int
    id: int
    http: str

    model_config = ConfigDict(from_attributes=True)