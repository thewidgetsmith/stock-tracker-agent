"""Additional SQLAlchemy ORM models for penny stock speculation feature."""

import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class PennyStockWatch(Base):
    """Penny stock watch list for tracking stocks under $5 with enhanced metrics."""

    __tablename__ = "penny_stock_watch"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, nullable=False, index=True)
    current_price = Column(Float, nullable=False)
    market_cap = Column(Float, nullable=True)
    volume_30d_avg = Column(Float, nullable=True)
    volatility_30d = Column(Float, nullable=True)  # Standard deviation of returns
    volatility_score = Column(Integer, nullable=True)  # 1-10 excitement rating
    sector = Column(String, nullable=True)
    exchange = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    discovered_at = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )
    last_updated = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )

    # Relationships
    virtual_positions = relationship("VirtualPosition", back_populates="penny_stock")
    speculation_alerts = relationship("SpeculationAlert", back_populates="penny_stock")

    def __repr__(self):
        return f"<PennyStockWatch(symbol='{self.symbol}', price=${self.current_price:.4f}, volatility={self.volatility_score}/10)>"


class SpeculationPortfolio(Base):
    """Virtual trading portfolio for penny stock speculation."""

    __tablename__ = "speculation_portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)  # Chat ID or user identifier
    portfolio_name = Column(String, nullable=False)
    virtual_balance = Column(
        Numeric(15, 2), nullable=False, default=10000.00
    )  # Starting balance
    total_invested = Column(Numeric(15, 2), nullable=False, default=0.00)
    total_value = Column(
        Numeric(15, 2), nullable=False, default=10000.00
    )  # Balance + positions value
    total_return_pct = Column(Float, nullable=False, default=0.0)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )
    last_updated = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )

    # Portfolio metadata
    strategy_type = Column(
        String, nullable=True
    )  # "aggressive", "conservative", "sector_focus", etc.
    description = Column(Text, nullable=True)

    # Relationships
    positions = relationship(
        "VirtualPosition", back_populates="portfolio", cascade="all, delete-orphan"
    )
    trades = relationship(
        "VirtualTrade", back_populates="portfolio", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<SpeculationPortfolio(user_id='{self.user_id}', name='{self.portfolio_name}', value=${self.total_value})>"


class VirtualPosition(Base):
    """Individual stock position within a speculation portfolio."""

    __tablename__ = "virtual_positions"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(
        Integer, ForeignKey("speculation_portfolios.id"), nullable=False, index=True
    )
    symbol = Column(String, nullable=False, index=True)
    penny_stock_id = Column(
        Integer, ForeignKey("penny_stock_watch.id"), nullable=True, index=True
    )

    # Position details
    quantity = Column(Integer, nullable=False)
    avg_cost_basis = Column(
        Numeric(10, 4), nullable=False
    )  # Average price paid per share
    total_cost = Column(Numeric(15, 2), nullable=False)  # Total amount invested
    current_value = Column(Numeric(15, 2), nullable=False, default=0.00)
    unrealized_pnl = Column(Numeric(15, 2), nullable=False, default=0.00)
    unrealized_pnl_pct = Column(Float, nullable=False, default=0.0)

    # Position metadata
    opened_at = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )
    last_updated = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )
    is_closed = Column(Boolean, default=False, nullable=False)
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    portfolio = relationship("SpeculationPortfolio", back_populates="positions")
    penny_stock = relationship("PennyStockWatch", back_populates="virtual_positions")

    def __repr__(self):
        return f"<VirtualPosition(symbol='{self.symbol}', quantity={self.quantity}, cost_basis=${self.avg_cost_basis})>"


class VirtualTrade(Base):
    """Record of virtual buy/sell transactions."""

    __tablename__ = "virtual_trades"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(
        Integer, ForeignKey("speculation_portfolios.id"), nullable=False, index=True
    )
    symbol = Column(String, nullable=False, index=True)

    # Trade details
    action = Column(String, nullable=False)  # "BUY" or "SELL"
    quantity = Column(Integer, nullable=False)
    price_per_share = Column(Numeric(10, 4), nullable=False)
    total_amount = Column(Numeric(15, 2), nullable=False)
    transaction_fee = Column(
        Numeric(5, 2), nullable=False, default=0.50
    )  # Simulate broker fees

    # Trade metadata
    executed_at = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )
    trade_type = Column(String, nullable=True)  # "market", "limit", etc.
    notes = Column(Text, nullable=True)

    # Relationships
    portfolio = relationship("SpeculationPortfolio", back_populates="trades")

    def __repr__(self):
        return f"<VirtualTrade(symbol='{self.symbol}', action='{self.action}', quantity={self.quantity}, price=${self.price_per_share})>"


class SpeculationAlert(Base):
    """Price movement alerts specifically for penny stocks."""

    __tablename__ = "speculation_alerts"

    id = Column(Integer, primary_key=True, index=True)
    penny_stock_id = Column(
        Integer, ForeignKey("penny_stock_watch.id"), nullable=False, index=True
    )
    user_id = Column(String, nullable=False, index=True)

    # Alert criteria
    alert_type = Column(
        String, nullable=False
    )  # "price_target", "volatility_spike", "volume_surge"
    trigger_price = Column(Numeric(10, 4), nullable=True)
    volatility_threshold = Column(Float, nullable=True)  # Percentage
    volume_threshold = Column(Float, nullable=True)  # Multiple of average

    # Alert status
    is_active = Column(Boolean, default=True, nullable=False)
    is_triggered = Column(Boolean, default=False, nullable=False)
    triggered_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )

    # Alert content
    message = Column(Text, nullable=True)

    # Relationships
    penny_stock = relationship("PennyStockWatch", back_populates="speculation_alerts")

    def __repr__(self):
        return f"<SpeculationAlert(symbol='{self.penny_stock.symbol if self.penny_stock else 'Unknown'}', type='{self.alert_type}', active={self.is_active})>"


class PortfolioPerformance(Base):
    """Daily portfolio performance snapshots for historical tracking."""

    __tablename__ = "portfolio_performance"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(
        Integer, ForeignKey("speculation_portfolios.id"), nullable=False, index=True
    )

    # Daily snapshot
    snapshot_date = Column(String, nullable=False)  # YYYY-MM-DD format
    total_value = Column(Numeric(15, 2), nullable=False)
    cash_balance = Column(Numeric(15, 2), nullable=False)
    invested_amount = Column(Numeric(15, 2), nullable=False)
    daily_return_pct = Column(Float, nullable=False, default=0.0)
    cumulative_return_pct = Column(Float, nullable=False, default=0.0)

    # Portfolio metrics
    num_positions = Column(Integer, nullable=False, default=0)
    largest_position_pct = Column(Float, nullable=False, default=0.0)
    portfolio_beta = Column(Float, nullable=True)  # Vs penny stock index
    sharpe_ratio = Column(Float, nullable=True)

    created_at = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )

    def __repr__(self):
        return f"<PortfolioPerformance(portfolio_id={self.portfolio_id}, date='{self.snapshot_date}', value=${self.total_value})>"


class SpeculationChallenge(Base):
    """Weekly/monthly challenges for users."""

    __tablename__ = "speculation_challenges"

    id = Column(Integer, primary_key=True, index=True)
    challenge_name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    challenge_type = Column(
        String, nullable=False
    )  # "weekly", "monthly", "sector", "theme"

    # Challenge parameters
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    criteria = Column(Text, nullable=True)  # JSON string with challenge rules

    # Challenge rewards
    virtual_reward = Column(
        Numeric(10, 2), nullable=True
    )  # Extra virtual money for winners
    badge_name = Column(String, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )

    def __repr__(self):
        return f"<SpeculationChallenge(name='{self.challenge_name}', type='{self.challenge_type}', active={self.is_active})>"
