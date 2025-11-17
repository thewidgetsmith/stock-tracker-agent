"""SQLAlchemy ORM models for the Sentinel application."""

import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from .database import Base


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
    created_at = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )
    alert_type = Column(String, default="daily", nullable=False)
    message_content = Column(Text, nullable=True)

    # Relationship with tracked stock
    stock = relationship("TrackedStock", back_populates="alerts")

    def __repr__(self):
        return f"<AlertHistory(stock_id={self.stock_id}, date='{self.alert_date}')>"


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
    timestamp = Column(
        DateTime,
        default=datetime.datetime.now(datetime.UTC),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )
    extra_data = Column(
        JSON, nullable=True
    )  # Renamed from 'metadata' to avoid conflict

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, chat_id='{self.chat_id}', type='{self.message_type}')>"


class PoliticianActivity(Base):
    """Politician activity entity for storing individual activity records."""

    __tablename__ = "politician_activities"

    id = Column(Integer, primary_key=True, index=True)
    politician_id = Column(
        Integer, ForeignKey("politician_profiles.id"), nullable=False, index=True
    )
    ticker = Column(String, nullable=False, index=True)
    activity_date = Column(DateTime, nullable=False, index=True)
    activity_type = Column(String, nullable=False)  # "Buy" or "Sale"
    amount_range = Column(String, nullable=False)  # e.g., "$1,001 - $15,000"
    source = Column(String, nullable=False)  # "House" or "Senate"
    report_date = Column(DateTime, nullable=True)
    asset_description = Column(Text, nullable=True)
    created_at = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )

    # For tracking analysis and alerts
    is_analyzed = Column(Boolean, default=False, nullable=False)
    analysis_notes = Column(Text, nullable=True)
    alert_sent = Column(Boolean, default=False, nullable=False)

    # Relationship with politician profile
    politician = relationship("PoliticianProfile", back_populates="activities")

    def __repr__(self):
        return f"<PoliticianActivity(politician_id={self.politician_id}, ticker='{self.ticker}', type='{self.activity_type}')>"


class PoliticianProfile(Base):
    """Politician profile entity for tracking individual politicians."""

    __tablename__ = "politician_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    slug = Column(String, unique=True, nullable=False, index=True)
    chamber = Column(String, nullable=False)  # "House" or "Senate"
    state = Column(String, nullable=True)
    party = Column(String, nullable=True)
    is_tracked = Column(Boolean, default=False, nullable=False)
    added_at = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )
    last_trade_check = Column(DateTime, nullable=True)

    # Relationship with congressional activities
    activities = relationship(
        "PoliticianActivity", back_populates="politician", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<PoliticianProfile(name='{self.name}', chamber='{self.chamber}')>"


class TrackedPolitician(Base):
    """Tracked politician entity for managing watchlist."""

    __tablename__ = "tracked_politicians"

    id = Column(Integer, primary_key=True, index=True)
    politician_id = Column(
        Integer, ForeignKey("politician_profiles.id"), nullable=False, index=True
    )
    added_at = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)
    alert_preferences = Column(JSON, nullable=True)  # Settings for what to alert on

    # Relationship with politician profile
    politician = relationship("PoliticianProfile")

    def __repr__(self):
        return f"<TrackedPolitician(politician_id={self.politician_id}, active={self.is_active})>"


class TrackedStock(Base):
    """Tracked stock entity for managing watchlist."""

    __tablename__ = "tracked_stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, nullable=False, index=True)
    added_at = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationship with alert history
    alerts = relationship(
        "AlertHistory", back_populates="stock", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<TrackedStock(symbol='{self.symbol}', active={self.is_active})>"


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
    first_interaction = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )
    last_interaction = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )
    preferences = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<UserSession(chat_id='{self.chat_id}', username='{self.username}')>"

    def update_last_interaction(self):
        """Update the last interaction timestamp."""
        self.last_interaction = datetime.datetime.now(datetime.UTC)
