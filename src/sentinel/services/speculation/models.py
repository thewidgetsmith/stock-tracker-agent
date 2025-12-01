"""Data models for virtual trading and speculation."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional


@dataclass
class TradeRequest:
    """Request for executing a virtual trade."""

    portfolio_id: int
    symbol: str
    action: str  # "BUY" or "SELL"
    quantity: int
    order_type: str = "MARKET"  # "MARKET" or "LIMIT"
    limit_price: Optional[Decimal] = None


@dataclass
class TradeResult:
    """Result of executing a virtual trade."""

    success: bool
    trade_id: Optional[int]
    executed_price: Optional[Decimal]
    total_amount: Optional[Decimal]
    new_position: Optional[Dict]
    error_message: Optional[str]
    portfolio_balance: Decimal


@dataclass
class PortfolioSummary:
    """Summary of portfolio performance and holdings."""

    portfolio_id: int
    portfolio_name: str
    total_value: Decimal
    cash_balance: Decimal
    invested_amount: Decimal
    total_return_pct: float
    daily_return_pct: float
    num_positions: int
    largest_position_pct: float
    risk_score: int  # 1-10 risk rating


@dataclass
class PositionSummary:
    """Summary of individual position."""

    symbol: str
    quantity: int
    avg_cost_basis: Decimal
    current_price: Decimal
    current_value: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_pct: float
    position_pct: float  # Percentage of total portfolio


@dataclass
class PerformanceReport:
    """Comprehensive portfolio performance report."""

    portfolio_summary: PortfolioSummary
    positions: List[PositionSummary]
    recent_trades: List[Dict]
    daily_performance: List[Dict]  # Last 30 days
    risk_metrics: Dict


@dataclass
class PortfolioRanking:
    """Portfolio ranking for leaderboards."""

    rank: int
    user_id: str
    portfolio_name: str
    total_return_pct: float
    total_value: Decimal
    risk_adjusted_return: float
    num_trades: int
    win_rate: float
