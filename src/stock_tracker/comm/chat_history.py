"""Chat history storage and management using SQLAlchemy ORM."""

from typing import Any, Dict, List, Optional

from ..db.database import get_session_sync
from ..db.repositories import ChatMessageRepository


class ChatHistoryManager:
    """Manages local storage of chat interactions using SQLAlchemy ORM."""

    def __init__(self):
        """Initialize the chat history manager."""
        # Ensure database tables are created
        from ..db.database import create_tables

        create_tables()

    def store_user_message(
        self,
        chat_id: str,
        message_text: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Store a user message.

        Args:
            chat_id: Telegram chat ID
            message_text: The message content
            user_id: User ID from Telegram
            username: Username or first name
            message_id: Telegram message ID
            metadata: Additional metadata as dict

        Returns:
            Message ID
        """
        with ChatMessageRepository() as repo:
            message = repo.store_user_message(
                chat_id=chat_id,
                message_text=message_text,
                user_id=user_id,
                username=username,
                message_id=message_id,
                metadata=metadata,
            )
            return int(message.id)

    def store_bot_response(
        self, chat_id: str, message_text: str, metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Store a bot response.

        Args:
            chat_id: Telegram chat ID
            message_text: The response content
            metadata: Additional metadata as dict

        Returns:
            Message ID
        """
        with ChatMessageRepository() as repo:
            message = repo.store_bot_response(
                chat_id=chat_id, message_text=message_text, metadata=metadata
            )
            return message.id

    def get_chat_history(
        self, chat_id: str, limit: int = 10, include_bot_messages: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieve recent chat history for a chat.

        Args:
            chat_id: Telegram chat ID
            limit: Maximum number of messages to retrieve
            include_bot_messages: Whether to include bot responses

        Returns:
            List of message dictionaries in chronological order (oldest first)
        """
        with ChatMessageRepository() as repo:
            messages = repo.get_chat_history(chat_id, limit, include_bot_messages)

            # Convert SQLAlchemy models to dictionaries
            return [
                {
                    "id": message.id,
                    "chat_id": message.chat_id,
                    "message_id": message.message_id,
                    "user_id": message.user_id,
                    "username": message.username,
                    "text": message.message_text,
                    "message_type": message.message_type,
                    "timestamp": message.timestamp,
                    "metadata": message.extra_data,
                }
                for message in messages
            ]

    def get_conversation_summary(self, chat_id: str, limit: int = 5) -> str:
        """
        Get a formatted conversation summary for the AI agent.

        Args:
            chat_id: Telegram chat ID
            limit: Number of recent messages to include

        Returns:
            Formatted conversation history string
        """
        with ChatMessageRepository() as repo:
            return repo.get_conversation_summary(chat_id, limit)

    def get_chat_statistics(self, chat_id: str) -> Dict[str, Any]:
        """
        Get statistics about a chat's message history.

        Args:
            chat_id: Telegram chat ID

        Returns:
            Dictionary containing chat statistics
        """
        with ChatMessageRepository() as repo:
            return repo.get_chat_statistics(chat_id)

    def cleanup_old_messages(self, days: int = 30) -> int:
        """
        Clean up messages older than specified days.

        Args:
            days: Number of days to keep messages

        Returns:
            Number of deleted messages
        """
        from datetime import datetime, timedelta

        from ..db.models import ChatMessage

        with get_session_sync() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            deleted_count = (
                session.query(ChatMessage)
                .filter(ChatMessage.timestamp < cutoff_date)
                .count()
            )

            session.query(ChatMessage).filter(
                ChatMessage.timestamp < cutoff_date
            ).delete()

            session.commit()

            print(f"Cleaned up {deleted_count} old chat messages")
            return deleted_count


# Global instance
chat_history_manager = ChatHistoryManager()
