from pydantic import BaseModel
from datetime import date
from decimal import Decimal

class PauseRequest(BaseModel):
    pause_start: date
    pause_end: date

class SubscriptionCreate(BaseModel):
    user_id: int
    monthly_rate: Decimal