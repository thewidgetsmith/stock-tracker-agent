"""Database configuration and session management."""

import os
from pathlib import Path
from typing import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

# Database configuration
DB_DIR = Path(__file__).parent.parent.parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "stock_tracker.db"

# SQLAlchemy setup
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite specific
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all ORM models
Base = declarative_base()


def get_engine() -> Engine:
    """Get the database engine."""
    return engine


def get_session() -> Generator[Session, None, None]:
    """
    Get a database session.

    Yields:
        Session: SQLAlchemy database session
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_session_sync() -> Session:
    """
    Get a synchronous database session.

    Returns:
        Session: SQLAlchemy database session
    """
    return SessionLocal()


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all database tables."""
    Base.metadata.drop_all(bind=engine)
