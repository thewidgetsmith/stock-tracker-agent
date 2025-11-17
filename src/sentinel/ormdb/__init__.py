"""Database module for SQLAlchemy ORM integration."""

# Import database configuration and session management
from .database import (
    Base,
    create_tables,
    drop_tables,
    get_engine,
    get_session,
    get_session_factory,
    get_session_sync,
    reset_database,
    check_database_health,
)

# Import all models
from .models import (
    AlertHistory,
    ChatMessage,
    PoliticianActivity,
    PoliticianProfile,
    TrackedPolitician,
    TrackedStock,
    UserSession,
)

# Import repositories
from .repositories import (
    AlertHistoryRepository,
    ChatMessageRepository,
    PoliticianActivityRepository,
    PoliticianProfileRepository,
    TrackedPoliticianRepository,
    TrackedStockRepository,
    UserSessionRepository,
)

__all__ = [
    # Database components
    "Base",
    "create_tables",
    "drop_tables",
    "get_engine", 
    "get_session",
    "get_session_factory",
    "get_session_sync",
    "reset_database",
    "check_database_health",
    # Models
    "AlertHistory",
    "ChatMessage",
    "PoliticianActivity",
    "PoliticianProfile",
    "TrackedPolitician",
    "TrackedStock", 
    "UserSession",
    # Repositories
    "AlertHistoryRepository",
    "ChatMessageRepository",
    "PoliticianActivityRepository",
    "PoliticianProfileRepository",
    "TrackedPoliticianRepository",
    "TrackedStockRepository",
    "UserSessionRepository",
]