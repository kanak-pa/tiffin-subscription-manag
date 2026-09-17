import enum
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Enum, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_order=True, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    subscriptions = relationship("Subscription", back_populates="owner")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    monthly_rate = Column(Float, default=3000.0)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="subscriptions")
    pause_logs = relationship("PauseLog", back_populates="subscription")

class PauseLog(Base):
    __tablename__ = "pause_logs"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    pause_start = Column(Date, nullable=False)
    pause_end = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    subscription = relationship("Subscription", back_populates="pause_logs")