"""Base repository class with common functionality."""

from typing import Optional

from sqlalchemy.orm import Session

from ..database import get_session_sync


class BaseRepository:
    """Base repository class providing common session management."""

    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session_sync()
        self._external_session = session is not None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._external_session:
            self.session.close()
