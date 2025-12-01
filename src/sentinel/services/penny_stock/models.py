"""Data models for penny stock service."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple


@dataclass
class PennyStockCandidate:
    """A potential penny stock candidate from screening."""

    symbol: str
    current_price: float
    market_cap: Optional[float]
    volume: Optional[int]
    avg_volume: Optional[int]
    sector: Optional[str]
    volatility_30d: Optional[float]
    volatility_score: int  # 1-10 rating
    volume_surge_ratio: float  # Current volume / average volume
    price_change_24h: float
    exchange: Optional[str]


@dataclass
class VolatilityMetrics:
    """Comprehensive volatility analysis for a penny stock."""

    symbol: str
    current_price: float
    volatility_30d: float  # 30-day volatility (standard deviation)
    volatility_score: int  # 1-10 simplified rating
    beta: Optional[float]  # Beta vs market
    volume_volatility: float  # Volume consistency
    price_range_30d: Tuple[float, float]  # (min, max) over 30 days
    avg_daily_move: float  # Average daily percentage move
    last_spike_date: Optional[datetime]  # Last >20% move


@dataclass
class ScreeningCriteria:
    """Criteria for screening penny stocks."""

    max_price: float = 5.00
    min_volume: int = 100000  # Minimum daily volume
    min_market_cap: Optional[float] = None
    max_market_cap: Optional[float] = None
    sectors: Optional[List[str]] = None
    min_volatility_score: int = 1
    max_volatility_score: int = 10
    exchanges: Optional[List[str]] = None  # ["NASDAQ", "NYSE", "AMEX"]
    volume_surge_min: float = 1.0  # Minimum volume surge ratio
