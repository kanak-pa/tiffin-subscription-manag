from pydantic import BaseModel
from datetime import date
from typing import Optional

# Base User Schema
class UserBase(BaseModel):
    name: str
    phone: str

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True

# Base Subscription Schema
class SubscriptionBase(BaseModel):
    user_id: int
    monthly_rate: float

class SubscriptionCreate(SubscriptionBase):
    pass

class SubscriptionResponse(SubscriptionBase):
    id: int
    status: str

    class Config:
        from_attributes = True

# Pause Request Schema
class PauseRequest(BaseModel):
    pause_start: date
    pause_end: date