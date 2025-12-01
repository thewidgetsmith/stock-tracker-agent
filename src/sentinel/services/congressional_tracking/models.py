"""Data models for congressional tracking service."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class CongressionalTrackingPortfolio:
    """Portfolio of tracked congressional members with metadata."""

    tracked_members: List[str]
    total_count: int
    active_count: int
    last_updated: datetime


@dataclass
class CongressionalTrackingResult:
    """Result of congressional member tracking operation."""

    member_name: str
    new_trades_count: int
    notable_trades_count: int
    alert_triggered: bool
    error: Optional[str]
    processing_time_ms: float
