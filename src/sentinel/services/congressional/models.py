"""Data models for congressional trading service."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional


@dataclass
class CongressionalTrade:
    """Congressional trade data container."""

    representative: str
    transaction_date: datetime
    ticker: str
    transaction_type: str  # "Buy" or "Sale"
    amount: str  # Usually a range like "$1,001 - $15,000"
    source: str  # "House" or "Senate"
    report_date: Optional[datetime] = None
    asset_description: Optional[str] = None


@dataclass
class CongressionalActivity:
    """Congressional member activity analysis."""

    representative: str
    recent_trades: List[CongressionalTrade]
    total_transactions: int
    buy_count: int
    sale_count: int
    active_tickers: List[str]
    analysis_period: str
    last_activity_date: Optional[datetime]


class TradeType(Enum):
    """Trade type classification."""

    BUY = "Buy"
    SALE = "Sale"
    BOTH = "Both"


class CongressionalBranch(Enum):
    """Congressional branch."""

    HOUSE = "house"
    SENATE = "senate"
    BOTH = "both"
