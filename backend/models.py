import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Enum, ForeignKey, Date, DateTime
from sqlalchemy.orm import relationship
from database import Base


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=False)

    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    monthly_rate = Column(Float, nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False)

    user = relationship("User", back_populates="subscriptions")
    pause_logs = relationship("PauseLog", back_populates="subscription", cascade="all, delete-orphan")
    transfers = relationship("SubscriptionTransfer", back_populates="subscription", cascade="all, delete-orphan")


class SubscriptionTransfer(Base):
    __tablename__ = "subscription_transfers"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    effective_date = Column(Date, nullable=False)

    subscription = relationship("Subscription", back_populates="transfers")


class PauseLog(Base):
    __tablename__ = "pause_logs"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    pause_start = Column(Date, nullable=False)
    pause_end = Column(Date, nullable=False)

    subscription = relationship("Subscription", back_populates="pause_logs")


class OutboxNotification(Base):
    __tablename__ = "outbox_notifications"

    id = Column(Integer, primary_key=True, index=True)
    recipient_phone = Column(String, nullable=False)
    message = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)