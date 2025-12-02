"""
Congressional tracking module for monitoring congressional trading activity.

This unified module provides comprehensive congressional trading functionality including:
- Trading data fetching from Quiver API (House and Senate)
- Trade analysis and processing
- Portfolio management for tracked members
- Database operations and caching
"""

from .api_client import QuiverAPIClient
from .congressional_operations import CongressionalOperations
from .data_processor import CongressionalDataProcessor
from .database import CongressionalDatabase
from .models import (
    CongressionalActivity,
    CongressionalBranch,
    CongressionalTrackingPortfolio,
    CongressionalTrackingResult,
    CongressionalTrade,
    TradeType,
)
from .portfolio_manager import CongressionalPortfolioManager
from .service import CongressionalTrackingService
from .tracker import CongressionalTracker

__all__ = [
    # Main service
    "CongressionalTrackingService",
    # Core operations
    "CongressionalOperations",
    # Components
    "CongressionalPortfolioManager",
    "CongressionalTracker",
    "CongressionalDatabase",
    "CongressionalDataProcessor",
    "QuiverAPIClient",
    # Models
    "CongressionalActivity",
    "CongressionalBranch",
    "CongressionalTrade",
    "CongressionalTrackingPortfolio",
    "CongressionalTrackingResult",
    "TradeType",
]
