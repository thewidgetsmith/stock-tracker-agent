"""Chat history storage and management using SQLite."""

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Thread-local storage for database connections
thread_local = threading.local()


class ChatHistoryManager:
    """Manages local storage of chat interactions using SQLite."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the chat history manager.

        Args:
            db_path: Path to SQLite database file. Defaults to data/stock_tracker.db
        """
        if db_path is None:
            # Default to data directory
            data_dir = Path(__file__).parent.parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = data_dir / "stock_tracker.db"

        self.db_path = str(db_path)
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local database connection."""
        if not hasattr(thread_local, "connection"):
            thread_local.connection = sqlite3.connect(self.db_path)
            thread_local.connection.row_factory = sqlite3.Row
        return thread_local.connection

    def _init_database(self):
        """Initialize the database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                message_id TEXT,
                user_id TEXT,
                username TEXT,
                message_text TEXT NOT NULL,
                message_type TEXT DEFAULT 'user',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """
        )

        # Create index for efficient queries
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_chat_timestamp
            ON chat_messages(chat_id, timestamp DESC)
        """
        )

        conn.commit()

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
            Database record ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO chat_messages
            (chat_id, message_id, user_id, username, message_text, message_type, metadata)
            VALUES (?, ?, ?, ?, ?, 'user', ?)
        """,
            (
                chat_id,
                message_id,
                user_id,
                username,
                message_text,
                json.dumps(metadata) if metadata else None,
            ),
        )

        conn.commit()
        return cursor.lastrowid

    def store_bot_response(
        self, chat_id: str, message_text: str, metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Store a bot response message.

        Args:
            chat_id: Telegram chat ID
            message_text: The bot response content
            metadata: Additional metadata as dict

        Returns:
            Database record ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO chat_messages
            (chat_id, message_text, message_type, username, metadata)
            VALUES (?, ?, 'bot', 'Stock Tracker Bot', ?)
        """,
            (chat_id, message_text, json.dumps(metadata) if metadata else None),
        )

        conn.commit()
        return cursor.lastrowid

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
        conn = self._get_connection()
        cursor = conn.cursor()

        if include_bot_messages:
            where_clause = "WHERE chat_id = ?"
            params = [chat_id]
        else:
            where_clause = "WHERE chat_id = ? AND message_type = 'user'"
            params = [chat_id]

        cursor.execute(
            f"""
            SELECT * FROM chat_messages
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            params + [limit],
        )

        rows = cursor.fetchall()

        # Convert to list of dicts and reverse to get chronological order (oldest first)
        messages = []
        for row in reversed(rows):
            message = {
                "id": row["id"],
                "chat_id": row["chat_id"],
                "message_id": row["message_id"],
                "user_id": row["user_id"],
                "username": row["username"],
                "text": row["message_text"],
                "message_type": row["message_type"],
                "timestamp": row["timestamp"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
            }
            messages.append(message)

        return messages

    def get_conversation_summary(self, chat_id: str, limit: int = 5) -> str:
        """
        Get a formatted conversation summary for the AI agent.

        Args:
            chat_id: Telegram chat ID
            limit: Number of recent messages to include

        Returns:
            Formatted conversation history string
        """
        messages = self.get_chat_history(chat_id, limit, include_bot_messages=True)

        if not messages:
            return "No previous conversation history."

        # Format messages for AI consumption
        formatted_messages = []
        for msg in messages:
            if msg["message_type"] == "user":
                sender = msg["username"] or "User"
                formatted_messages.append(f"{sender}: {msg['text']}")
            else:
                formatted_messages.append(f"Bot: {msg['text']}")

        return "\n".join(formatted_messages)

    def cleanup_old_messages(self, days: int = 30):
        """
        Clean up messages older than specified days.

        Args:
            days: Number of days to keep messages
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM chat_messages
            WHERE timestamp < datetime('now', '-{} days')
        """.format(
                days
            )
        )

        deleted_count = cursor.rowcount
        conn.commit()

        print(f"Cleaned up {deleted_count} old chat messages")
        return deleted_count

    def get_chat_statistics(self, chat_id: str) -> Dict[str, Any]:
        """
        Get statistics for a chat.

        Args:
            chat_id: Telegram chat ID

        Returns:
            Dictionary with chat statistics
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                COUNT(*) as total_messages,
                COUNT(CASE WHEN message_type = 'user' THEN 1 END) as user_messages,
                COUNT(CASE WHEN message_type = 'bot' THEN 1 END) as bot_messages,
                MIN(timestamp) as first_message,
                MAX(timestamp) as last_message
            FROM chat_messages
            WHERE chat_id = ?
        """,
            (chat_id,),
        )

        row = cursor.fetchone()

        return {
            "total_messages": row["total_messages"],
            "user_messages": row["user_messages"],
            "bot_messages": row["bot_messages"],
            "first_message": row["first_message"],
            "last_message": row["last_message"],
        }


# Global instance
chat_history_manager = ChatHistoryManager()
