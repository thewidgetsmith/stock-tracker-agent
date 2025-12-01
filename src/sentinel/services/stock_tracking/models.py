"""Data models for stock tracking service."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional


class MovementThreshold(Enum):
    """Price movement significance thresholds."""

    MINOR = 0.005  # 0.5%
    MODERATE = 0.01  # 1%
    SIGNIFICANT = 0.05  # 5%
    MAJOR = 0.10  # 10%


@dataclass
class StockAnalysis:
    """Stock analysis data container."""

    symbol: str
    current_price: float
    previous_close: float
    price_change: float
    price_change_percent: float
    volume: Optional[int]
    market_cap: Optional[float]
    analysis_timestamp: datetime
    is_significant_movement: bool


@dataclass
class TrackingPortfolio:
    """Portfolio of tracked stocks with metadata."""

    tracked_stocks: List[str]
    total_count: int
    active_count: int
    last_updated: datetime


@dataclass
class StockTrackingResult:
    """Result of stock tracking operation."""

    symbol: str
    analysis: Optional[StockAnalysis]
    alert_triggered: bool
    error: Optional[str]
    processing_time_ms: float
