"""Repository for chat message operations."""

from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from ..models import ChatMessage
from .base import BaseRepository


class ChatMessageRepository(BaseRepository):
    """Repository for chat message operations."""

    def store_user_message(
        self,
        chat_id: str,
        message_text: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatMessage:
        """Store a user message."""
        message = ChatMessage(
            chat_id=chat_id,
            message_text=message_text,
            message_type="user",
            user_id=user_id,
            username=username,
            message_id=message_id,
            extra_data=metadata,
        )

        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)

        return message

    def store_bot_response(
        self, chat_id: str, message_text: str, metadata: Optional[Dict[str, Any]] = None
    ) -> ChatMessage:
        """Store a bot response."""
        message = ChatMessage(
            chat_id=chat_id,
            message_text=message_text,
            message_type="bot",
            username="Sentinel Bot",
            extra_data=metadata,
        )

        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)

        return message

    def get_chat_history(
        self, chat_id: str, limit: int = 10, include_bot_messages: bool = True
    ) -> List[ChatMessage]:
        """Get recent chat history for a chat."""
        query = self.session.query(ChatMessage).filter(ChatMessage.chat_id == chat_id)

        if not include_bot_messages:
            query = query.filter(ChatMessage.message_type == "user")

        messages = query.order_by(desc(ChatMessage.timestamp)).limit(limit).all()

        # Reverse to get chronological order (oldest first)
        return list(reversed(messages))

    def get_conversation_summary(self, chat_id: str, limit: int = 5) -> str:
        """Get a formatted conversation summary."""
        messages = self.get_chat_history(chat_id, limit, include_bot_messages=True)

        if not messages:
            return "No previous conversation history."

        summary_lines = []
        for message in messages:
            if message.message_type == "user":
                summary_lines.append(f"User: {message.message_text}")
            else:
                summary_lines.append(f"Bot: {message.message_text}")

        return "\\n".join(summary_lines)

    def get_chat_statistics(self, chat_id: str) -> Dict[str, Any]:
        """Get statistics for a chat."""
        total_messages = (
            self.session.query(ChatMessage)
            .filter(ChatMessage.chat_id == chat_id)
            .count()
        )

        user_messages = (
            self.session.query(ChatMessage)
            .filter(
                and_(ChatMessage.chat_id == chat_id, ChatMessage.message_type == "user")
            )
            .count()
        )

        bot_messages = (
            self.session.query(ChatMessage)
            .filter(
                and_(ChatMessage.chat_id == chat_id, ChatMessage.message_type == "bot")
            )
            .count()
        )

        first_message = (
            self.session.query(ChatMessage)
            .filter(ChatMessage.chat_id == chat_id)
            .order_by(ChatMessage.timestamp)
            .first()
        )

        last_message = (
            self.session.query(ChatMessage)
            .filter(ChatMessage.chat_id == chat_id)
            .order_by(desc(ChatMessage.timestamp))
            .first()
        )

        return {
            "total_messages": total_messages,
            "user_messages": user_messages,
            "bot_messages": bot_messages,
            "first_message": first_message.timestamp if first_message else None,
            "last_message": last_message.timestamp if last_message else None,
        }
