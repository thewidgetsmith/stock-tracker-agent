"""Database configuration and session management with enhanced features."""

import os
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import Engine as EngineType
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from ..config.logging import get_logger
from ..config.settings import get_settings

# Get logger for this module
logger = get_logger(__name__)

# Base class for all ORM models
Base = declarative_base()

# Global engine and session factory
_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def _configure_sqlite_for_performance(dbapi_connection, connection_record):
    """Configure SQLite for better performance and reliability."""
    with dbapi_connection:
        # Enable WAL mode for better concurrency
        dbapi_connection.execute("PRAGMA journal_mode=WAL")
        # Enable foreign key constraints
        dbapi_connection.execute("PRAGMA foreign_keys=ON")
        # Optimize for performance
        dbapi_connection.execute("PRAGMA synchronous=NORMAL")
        dbapi_connection.execute("PRAGMA cache_size=1000")
        dbapi_connection.execute("PRAGMA temp_store=MEMORY")


def create_engine_from_settings() -> Engine:
    """Create database engine using application settings."""
    settings = get_settings()

    # Get database URL from settings
    database_url = settings.get_database_url()

    logger.info(
        "Creating database engine",
        url_type="sqlite" if "sqlite" in database_url else "other",
        echo_sql=settings.database_echo_sql,
    )

    # Configure engine parameters based on database type
    engine_kwargs = {
        "echo": settings.database_echo_sql,
        "pool_pre_ping": settings.database_pool_pre_ping,
        "pool_recycle": settings.database_pool_recycle,
    }

    # SQLite-specific configuration
    if "sqlite" in database_url:
        engine_kwargs.update(
            {
                "connect_args": {
                    "check_same_thread": False,
                    "timeout": 30,  # 30 second timeout for connections
                },
                "poolclass": StaticPool,
            }
        )
    else:
        # PostgreSQL/MySQL configuration
        engine_kwargs.update(
            {
                "pool_size": 5,
                "max_overflow": 10,
            }
        )

    engine = create_engine(database_url, **engine_kwargs)

    # Configure SQLite for performance if using SQLite
    if "sqlite" in database_url:
        event.listen(engine, "connect", _configure_sqlite_for_performance)

    return engine


def get_engine() -> Engine:
    """Get the database engine, creating it if necessary."""
    global _engine

    if _engine is None:
        _engine = create_engine_from_settings()
        logger.info("Database engine initialized")

    return _engine


def get_session_factory() -> sessionmaker:
    """Get the session factory, creating it if necessary."""
    global _SessionLocal

    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
            expire_on_commit=False,  # Keep objects accessible after commit
        )
        logger.debug("Session factory created")

    return _SessionLocal


def get_session() -> Generator[Session, None, None]:
    """
    Get a database session with automatic cleanup.

    Yields:
        Session: SQLAlchemy database session with automatic transaction management
    """
    SessionFactory = get_session_factory()
    session = SessionFactory()

    try:
        logger.debug("Database session created")
        yield session
        session.commit()
        logger.debug("Database session committed")
    except Exception as e:
        session.rollback()
        logger.error("Database session rolled back", error=str(e), exc_info=True)
        raise
    finally:
        session.close()
        logger.debug("Database session closed")


def get_session_sync() -> Session:
    """
    Get a synchronous database session.

    Returns:
        Session: SQLAlchemy database session (caller responsible for closing)
    """
    SessionFactory = get_session_factory()
    session = SessionFactory()
    logger.debug("Synchronous database session created")
    return session


def create_tables():
    """Create all database tables."""
    engine = get_engine()

    logger.info("Creating database tables")
    Base.metadata.create_all(bind=engine)

    logger.info("Database tables created successfully")
    # APScheduler will create its tables automatically when first started
    logger.info("APScheduler tables will be created on first use")


def drop_tables():
    """Drop all database tables."""
    engine = get_engine()

    logger.warning("Dropping all database tables")
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped")


def check_database_health() -> dict:
    """
    Check database connectivity and return health information.

    Returns:
        dict: Database health status and metrics
    """
    try:
        engine = get_engine()

        # Use the session generator properly
        session_gen = get_session()
        session = next(session_gen)

        try:
            # Simple connectivity test using text() for raw SQL
            from sqlalchemy import text

            result = session.execute(text("SELECT 1 as health_check"))
            health_check = result.scalar()

            # Get connection pool info
            pool = engine.pool
            pool_info = {
                "pool_size": getattr(pool, "size", "N/A"),
                "checked_in": getattr(pool, "checkedin", "N/A"),
                "checked_out": getattr(pool, "checkedout", "N/A"),
                "overflow": getattr(pool, "overflow", "N/A"),
            }

            logger.info("Database health check successful", pool_info=pool_info)

            return {
                "status": "healthy",
                "connectivity": health_check == 1,
                "pool_info": pool_info,
                "database_url": get_settings().get_database_url().split("@")[0]
                + "@***",  # Hide credentials
            }
        finally:
            # Close the session properly
            try:
                next(session_gen)
            except StopIteration:
                pass

    except Exception as e:
        logger.error("Database health check failed", error=str(e), exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "connectivity": False,
        }


def reset_database():
    """Reset database by dropping and recreating all tables."""
    logger.warning("Resetting database - dropping and recreating all tables")

    drop_tables()
    create_tables()

    logger.info("Database reset completed")


# Legacy compatibility - maintain SQLALCHEMY_DATABASE_URL for backward compatibility
def get_database_url() -> str:
    """Get database URL for backward compatibility."""
    return get_settings().get_database_url()


# Legacy global variables for backward compatibility
SQLALCHEMY_DATABASE_URL = get_database_url()
