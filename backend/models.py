import enum
from sqlalchemy import Column, Integer, String, Float, Enum, ForeignKey, Date
from sqlalchemy.orm import relationship
from database import Base

# Subscription status options
class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=False)

    # Relationship to Subscriptions
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    monthly_rate = Column(Float, nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False)

    # Relationships
    user = relationship("User", back_populates="subscriptions")
    pause_logs = relationship("PauseLog", back_populates="subscription", cascade="all, delete-orphan")

class PauseLog(Base):
    __tablename__ = "pause_logs"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    pause_start = Column(Date, nullable=False)
    pause_end = Column(Date, nullable=False)

    # Relationship back to Subscription
    subscription = relationship("Subscription", back_populates="pause_logs")