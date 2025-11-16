"""Repository classes for database operations using SQLAlchemy ORM."""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from .database import get_session_sync
from .models import AlertHistory, ChatMessage, TrackedStock, UserSession


class ChatMessageRepository:
    """Repository for chat message operations."""

    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session_sync()
        self._external_session = session is not None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._external_session:
            self.session.close()

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


class TrackedStockRepository:
    """Repository for tracked stock operations."""

    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session_sync()
        self._external_session = session is not None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._external_session:
            self.session.close()

    def add_stock(self, symbol: str) -> TrackedStock:
        """Add a stock to the tracking list."""
        # Check if stock already exists
        existing_stock = self.get_stock_by_symbol(symbol)
        if existing_stock:
            if not existing_stock.is_active:
                # Reactivate if it was deactivated
                existing_stock.is_active = True
                self.session.commit()
            return existing_stock

        stock = TrackedStock(symbol=symbol.upper())
        self.session.add(stock)
        self.session.commit()
        self.session.refresh(stock)

        return stock

    def remove_stock(self, symbol: str) -> bool:
        """Remove a stock from tracking (soft delete)."""
        stock = self.get_stock_by_symbol(symbol)
        if stock and stock.is_active:
            stock.is_active = False
            self.session.commit()
            return True
        return False

    def get_stock_by_symbol(self, symbol: str) -> Optional[TrackedStock]:
        """Get a tracked stock by symbol."""
        return (
            self.session.query(TrackedStock)
            .filter(TrackedStock.symbol == symbol.upper())
            .first()
        )

    def get_all_active_stocks(self) -> List[TrackedStock]:
        """Get all actively tracked stocks."""
        return (
            self.session.query(TrackedStock)
            .filter(TrackedStock.is_active == True)
            .order_by(TrackedStock.symbol)
            .all()
        )

    def get_stock_symbols(self) -> List[str]:
        """Get list of all tracked stock symbols."""
        stocks = self.get_all_active_stocks()
        return [stock.symbol for stock in stocks]


class AlertHistoryRepository:
    """Repository for alert history operations."""

    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session_sync()
        self._external_session = session is not None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._external_session:
            self.session.close()

    def add_alert(
        self,
        stock_symbol: str,
        alert_date: str,
        alert_type: str = "daily",
        message_content: Optional[str] = None,
    ) -> AlertHistory:
        """Add an alert to history."""
        # Get or create the tracked stock
        with TrackedStockRepository(self.session) as stock_repo:
            stock = stock_repo.add_stock(stock_symbol)

        alert = AlertHistory(
            stock_id=stock.id,
            alert_date=alert_date,
            alert_type=alert_type,
            message_content=message_content,
        )

        self.session.add(alert)
        self.session.commit()
        self.session.refresh(alert)

        return alert

    def get_alerts_for_stock(self, stock_symbol: str) -> List[AlertHistory]:
        """Get all alerts for a specific stock."""
        return (
            self.session.query(AlertHistory)
            .join(TrackedStock)
            .filter(TrackedStock.symbol == stock_symbol.upper())
            .order_by(desc(AlertHistory.alert_date))
            .all()
        )

    def get_alerts_for_date(self, alert_date: str) -> List[AlertHistory]:
        """Get all alerts for a specific date."""
        return (
            self.session.query(AlertHistory)
            .filter(AlertHistory.alert_date == alert_date)
            .all()
        )

    def has_alert_been_sent(self, stock_symbol: str, alert_date: str) -> bool:
        """Check if an alert has already been sent for a stock on a specific date."""
        count = (
            self.session.query(AlertHistory)
            .join(TrackedStock)
            .filter(
                and_(
                    TrackedStock.symbol == stock_symbol.upper(),
                    AlertHistory.alert_date == alert_date,
                )
            )
            .count()
        )

        return count > 0

    def get_alert_dates_for_stock(self, stock_symbol: str) -> List[str]:
        """Get all alert dates for a specific stock."""
        alerts = self.get_alerts_for_stock(stock_symbol)
        return [alert.alert_date for alert in alerts]


class UserSessionRepository:
    """Repository for user session operations."""

    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session_sync()
        self._external_session = session is not None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._external_session:
            self.session.close()

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
