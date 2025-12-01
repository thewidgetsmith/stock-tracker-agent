"""
Repository classes for database operations using SQLAlchemy ORM.

This module maintains backward compatibility by re-exporting all repository classes
from the new modular structure in the repositories/ directory.
"""

# Re-export all repository classes from the new modular structure
from .repositories import (
    AlertHistoryRepository,
    BaseRepository,
    ChatMessageRepository,
    PoliticianActivityRepository,
    PoliticianProfileRepository,
    TrackedPoliticianRepository,
    TrackedStockRepository,
    UserSessionRepository,
)

__all__ = [
    "BaseRepository",
    "AlertHistoryRepository",
    "ChatMessageRepository",
    "PoliticianActivityRepository",
    "PoliticianProfileRepository",
    "TrackedPoliticianRepository",
    "TrackedStockRepository",
    "UserSessionRepository",
]
