from pydantic import BaseModel, ConfigDict
from datetime import datetime

class VKCredsRequestAdd(BaseModel):
    creds: str

class VKAccountCredRequestAdd(BaseModel):
    login: str
    password: str

class VKAccountCredRequestAutoCurlAdd(BaseModel):
    creds: str
    groups: str