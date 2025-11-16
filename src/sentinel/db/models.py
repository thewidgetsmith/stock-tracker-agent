"""SQLAlchemy ORM models for the Sentinel application."""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from .database import Base


class ChatMessage(Base):
    """Chat message entity for storing conversation history."""

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, nullable=False, index=True)
    message_id = Column(String, nullable=True)
    user_id = Column(String, nullable=True)
    username = Column(String, nullable=True)
    message_text = Column(Text, nullable=False)
    message_type = Column(String, default="user", nullable=False)  # 'user' or 'bot'
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    extra_data = Column(
        JSON, nullable=True
    )  # Renamed from 'metadata' to avoid conflict

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, chat_id='{self.chat_id}', type='{self.message_type}')>"


class TrackedStock(Base):
    """Tracked stock entity for managing watchlist."""

    __tablename__ = "tracked_stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, nullable=False, index=True)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationship with alert history
    alerts = relationship(
        "AlertHistory", back_populates="stock", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<TrackedStock(symbol='{self.symbol}', active={self.is_active})>"


class AlertHistory(Base):
    """Alert history entity for tracking when alerts were sent."""

    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(
        Integer, ForeignKey("tracked_stocks.id"), nullable=False, index=True
    )
    alert_date = Column(
        String, nullable=False
    )  # Store as YYYY-MM-DD string for compatibility
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    alert_type = Column(String, default="daily", nullable=False)
    message_content = Column(Text, nullable=True)

    # Relationship with tracked stock
    stock = relationship("TrackedStock", back_populates="alerts")

    def __repr__(self):
        return f"<AlertHistory(stock_id={self.stock_id}, date='{self.alert_date}')>"


class UserSession(Base):
    """User session entity for managing user states and preferences."""

    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(String, nullable=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    language_code = Column(String, default="en", nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    first_interaction = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_interaction = Column(DateTime, default=datetime.utcnow, nullable=False)
    preferences = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<UserSession(chat_id='{self.chat_id}', username='{self.username}')>"

    def update_last_interaction(self):
        """Update the last interaction timestamp."""
        self.last_interaction = datetime.utcnow()
