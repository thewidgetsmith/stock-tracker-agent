"""Database migration utilities for SQLAlchemy."""

from pathlib import Path
from typing import Dict, List

from .database import create_tables, get_session_sync
from .repositories import AlertHistoryRepository, TrackedStockRepository

if __name__ == "__main__":
    # Run migration
    pass
