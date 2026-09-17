from pydantic import BaseModel
from datetime import date
from typing import Optional
from models import SubscriptionStatus

class UserRegister(BaseModel):
    name: str
    phone: str

class UserLogin(BaseModel):
    phone: str

class UserResponse(BaseModel):
    id: int
    name: str
    phone: str

    class Config:
        from_attributes = True

class PauseRequest(BaseModel):
    pause_start: date
    pause_end: date