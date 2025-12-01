"""Repository for user session operations."""

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from ..models import UserSession
from .base import BaseRepository


class UserSessionRepository(BaseRepository):
    """Repository for user session operations."""

    def create_or_update_session(
        self,
        chat_id: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: Optional[str] = None,
    ) -> UserSession:
        """Create or update a user session."""
        session = self.get_session_by_chat_id(chat_id)

        if session:
            # Update existing session
            session.user_id = user_id or session.user_id
            session.username = username or session.username
            session.first_name = first_name or session.first_name
            session.last_name = last_name or session.last_name
            session.language_code = language_code or session.language_code
            session.update_last_interaction()
        else:
            # Create new session
            session = UserSession(
                chat_id=chat_id,
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code or "en",
            )
            self.session.add(session)

        self.session.commit()
        self.session.refresh(session)

        return session

    def get_session_by_chat_id(self, chat_id: str) -> Optional[UserSession]:
        """Get user session by chat ID."""
        return (
            self.session.query(UserSession)
            .filter(UserSession.chat_id == chat_id)
            .first()
        )

    def update_preferences(self, chat_id: str, preferences: Dict[str, Any]) -> bool:
        """Update user preferences."""
        session = self.get_session_by_chat_id(chat_id)
        if session:
            session.preferences = preferences
            session.update_last_interaction()
            self.session.commit()
            return True
        return False
