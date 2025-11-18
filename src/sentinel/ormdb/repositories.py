"""Repository classes for database operations using SQLAlchemy ORM."""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from .database import get_session_sync
from .models import (
    AlertHistory,
    ChatMessage,
    PoliticianActivity,
    PoliticianProfile,
    TrackedPolitician,
    TrackedStock,
    UserSession,
)


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


class PoliticianProfileRepository:
    """Repository for politician profile operations."""

    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session_sync()
        self._external_session = session is not None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._external_session:
            self.session.close()

    def add_politician(
        self,
        name: str,
        chamber: str,
        state: Optional[str] = None,
        party: Optional[str] = None,
    ) -> PoliticianProfile:
        """Add a politician to the database."""
        # Check if politician already exists
        existing_politician = self.get_politician_by_name(name)
        if existing_politician:
            return existing_politician

        # Generate a slug from the name
        slug = name.lower().replace(" ", "-").replace(".", "")

        politician = PoliticianProfile(
            name=name, slug=slug, chamber=chamber, state=state, party=party
        )
        self.session.add(politician)
        self.session.commit()
        self.session.refresh(politician)

        return politician

    def get_politician_by_name(self, name: str) -> Optional[PoliticianProfile]:
        """Get a politician by name."""
        return (
            self.session.query(PoliticianProfile)
            .filter(PoliticianProfile.name == name)
            .first()
        )

    def get_politician_by_slug(self, slug: str) -> Optional[PoliticianProfile]:
        """Get a politician by slugified name."""
        return (
            self.session.query(PoliticianProfile)
            .filter(PoliticianProfile.slug == slug)
            .first()
        )

    def get_politician_by_id(self, politician_id: int) -> Optional[PoliticianProfile]:
        """Get a politician by ID."""
        return (
            self.session.query(PoliticianProfile)
            .filter(PoliticianProfile.id == politician_id)
            .first()
        )

    def get_politicians_by_chamber(self, chamber: str) -> List[PoliticianProfile]:
        """Get all politicians from a specific chamber."""
        return (
            self.session.query(PoliticianProfile)
            .filter(PoliticianProfile.chamber == chamber)
            .order_by(PoliticianProfile.name)
            .all()
        )

    def get_tracked_politicians(self) -> List[PoliticianProfile]:
        """Get all politicians that are being tracked."""
        return (
            self.session.query(PoliticianProfile)
            .filter(PoliticianProfile.is_tracked == True)
            .order_by(PoliticianProfile.name)
            .all()
        )

    def update_politician_tracking(self, name: str, is_tracked: bool) -> bool:
        """Update tracking status for a politician."""
        politician = self.get_politician_by_name(name)
        if politician:
            politician.is_tracked = is_tracked
            self.session.commit()
            return True
        return False

    def is_data_stale(self, name: str, hours: int = 12) -> bool:
        """
        Check if politician trading data is stale (older than specified hours).
        
        Args:
            name: Name of the politician
            hours: Number of hours to consider data stale (default: 12)
            
        Returns:
            True if data is stale or has never been checked, False if fresh
        """
        politician = self.get_politician_by_name(name)
        if not politician or not getattr(politician, 'last_trade_check', None):
            return True  # No data or never checked
            
        from datetime import datetime, timedelta, timezone
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Ensure both timestamps are timezone-aware for comparison
        last_check = politician.last_trade_check
        if last_check.tzinfo is None:
            last_check = last_check.replace(tzinfo=timezone.utc)
            
        return last_check < cutoff_time

    def update_last_trade_check(self, name: str) -> bool:
        """
        Update the last_trade_check timestamp for a politician.
        
        Args:
            name: Name of the politician
            
        Returns:
            True if updated successfully, False otherwise
        """
        politician = self.get_politician_by_name(name)
        if politician:
            from datetime import datetime, timezone
            politician.last_trade_check = datetime.now(timezone.utc)
            self.session.commit()
            return True
        return False


class PoliticianActivityRepository:
    """Repository for politician activity operations."""

    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session_sync()
        self._external_session = session is not None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._external_session:
            self.session.close()

    def add_activity(
        self,
        politician_name: str,
        ticker: str,
        transaction_date: datetime,
        transaction_type: str,
        amount_range: str,
        source: str,
        chamber: str,
        report_date: Optional[datetime] = None,
        asset_description: Optional[str] = None,
    ) -> PoliticianActivity:
        """Add a politician activity to the database."""
        # Get or create the politician
        with PoliticianProfileRepository(self.session) as politician_repo:
            politician = politician_repo.add_politician(politician_name, chamber)
        # Check if this activity already exists
        existing_activity = (
            self.session.query(PoliticianActivity)
            .filter(
                and_(
                    PoliticianActivity.politician_id == politician.id,
                    PoliticianActivity.ticker == ticker.upper(),
                    PoliticianActivity.activity_date == transaction_date,
                    PoliticianActivity.activity_type == transaction_type,
                    PoliticianActivity.amount_range == amount_range,
                )
            )
            .first()
        )

        if existing_activity:
            return existing_activity

        activity = PoliticianActivity(
            politician_id=politician.id,
            ticker=ticker.upper(),
            activity_date=transaction_date,
            activity_type=transaction_type,
            amount_range=amount_range,
            source=source,
            report_date=report_date,
            asset_description=asset_description,
        )

        self.session.add(activity)
        self.session.commit()
        self.session.refresh(activity)

        return activity

    def get_activities_by_politician(
        self, politician_name: str
    ) -> List[PoliticianActivity]:
        """Get all activities for a specific politician."""
        return (
            self.session.query(PoliticianActivity)
            .join(PoliticianProfile)
            .filter(PoliticianProfile.name == politician_name)
            .order_by(desc(PoliticianActivity.activity_date))
            .all()
        )

    def get_activities_by_ticker(self, ticker: str) -> List[PoliticianActivity]:
        """Get all activities for a specific ticker."""
        return (
            self.session.query(PoliticianActivity)
            .filter(PoliticianActivity.ticker == ticker.upper())
            .order_by(desc(PoliticianActivity.activity_date))
            .all()
        )

    def get_recent_activities_by_politician(self, politician_name: str, days: int = 30) -> List[PoliticianActivity]:
        """Get recent activities for a specific politician within specified days."""
        cutoff_date = datetime.now() - timedelta(days=days)
        return (
            self.session.query(PoliticianActivity)
            .join(PoliticianProfile)
            .filter(
                and_(
                    PoliticianProfile.name == politician_name,
                    PoliticianActivity.activity_date >= cutoff_date,
                )
            )
            .order_by(desc(PoliticianActivity.activity_date))
            .all()
        )

    def get_recent_activities(self, days: int = 7) -> List[PoliticianActivity]:
        """Get recent activities within specified days."""
        cutoff_date = datetime.now() - timedelta(days=days)
        return (
            self.session.query(PoliticianActivity)
            .filter(PoliticianActivity.activity_date >= cutoff_date)
            .order_by(desc(PoliticianActivity.activity_date))
            .all()
        )

    def get_unanalyzed_activities(self) -> List[PoliticianActivity]:
        """Get activities that haven't been analyzed yet."""
        return (
            self.session.query(PoliticianActivity)
            .filter(PoliticianActivity.is_analyzed == False)
            .order_by(desc(PoliticianActivity.activity_date))
            .all()
        )

    def mark_activity_analyzed(
        self, activity_id: int, analysis_notes: Optional[str] = None
    ) -> bool:
        """Mark an activity as analyzed."""
        activity = (
            self.session.query(PoliticianActivity)
            .filter(PoliticianActivity.id == activity_id)
            .first()
        )

        if activity:
            activity.is_analyzed = True
            if analysis_notes:
                activity.analysis_notes = analysis_notes
            self.session.commit()
            return True
        return False

    def mark_alert_sent(self, activity_id: int) -> bool:
        """Mark that an alert has been sent for this activity."""
        activity = (
            self.session.query(PoliticianActivity)
            .filter(PoliticianActivity.id == activity_id)
            .first()
        )

        if activity:
            activity.alert_sent = True
            self.session.commit()
            return True
        return False


class TrackedPoliticianRepository:
    """Repository for tracked politician operations."""

    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session_sync()
        self._external_session = session is not None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._external_session:
            self.session.close()

    def add_tracked_politician(
        self,
        politician_name: str,
        chamber: Optional[str] = "House",
        alert_preferences: Optional[Dict[str, Any]] = None,
    ) -> TrackedPolitician:
        """Add a politician to the tracking list."""
        # Get or create the politician
        with PoliticianProfileRepository(self.session) as politician_repo:
            politician = politician_repo.add_politician(politician_name, chamber)
            politician_repo.update_politician_tracking(politician_name, True)

        # Check if already being tracked
        existing_tracked = (
            self.session.query(TrackedPolitician)
            .filter(TrackedPolitician.politician_id == politician.id)
            .first()
        )

        if existing_tracked:
            if not existing_tracked.is_active:
                existing_tracked.is_active = True
                self.session.commit()
            return existing_tracked

        tracked_politician = TrackedPolitician(
            politician_id=politician.id, alert_preferences=alert_preferences
        )
        self.session.add(tracked_politician)
        self.session.commit()
        self.session.refresh(tracked_politician)

        return tracked_politician

    def remove_tracked_politician(self, politician_name: str) -> bool:
        """Remove a politician from tracking (soft delete)."""
        # Get the politician
        with PoliticianProfileRepository(self.session) as politician_repo:
            politician = politician_repo.get_politician_by_name(politician_name)
        if not politician:
            return False

        tracked_politician = (
            self.session.query(TrackedPolitician)
            .filter(TrackedPolitician.politician_id == politician.id)
            .first()
        )

        if tracked_politician and tracked_politician.is_active:
            tracked_politician.is_active = False
            # Also update the politician tracking status
            with PoliticianProfileRepository(self.session) as politician_repo:
                politician_repo.update_politician_tracking(politician_name, False)
            self.session.commit()
            return True

        return False

    def get_all_tracked_politicians(self) -> List[TrackedPolitician]:
        """Get all actively tracked politicians with eager loading."""
        from sqlalchemy.orm import joinedload
        return (
            self.session.query(TrackedPolitician)
            .options(joinedload(TrackedPolitician.politician))
            .filter(TrackedPolitician.is_active == True)
            .join(PoliticianProfile)
            .order_by(PoliticianProfile.name)
            .all()
        )

    def is_politician_tracked(self, politician_name: str) -> bool:
        """Check if a politician is being tracked."""
        with PoliticianProfileRepository(self.session) as politician_repo:
            politician = politician_repo.get_politician_by_name(politician_name)

        if not politician:
            return False

        tracked_politician = (
            self.session.query(TrackedPolitician)
            .filter(
                and_(
                    TrackedPolitician.politician_id == politician.id,
                    TrackedPolitician.is_active == True,
                )
            )
            .first()
        )

        return tracked_politician is not None

    def update_alert_preferences(
        self, politician_name: str, alert_preferences: Dict[str, Any]
    ) -> bool:
        """Update alert preferences for a tracked politician."""
        with PoliticianProfileRepository(self.session) as politician_repo:
            politician = politician_repo.get_politician_by_name(politician_name)
        if not politician:
            return False

        tracked_politician = (
            self.session.query(TrackedPolitician)
            .filter(TrackedPolitician.politician_id == politician.id)
            .first()
        )

        if tracked_politician:
            tracked_politician.alert_preferences = alert_preferences
            self.session.commit()
            return True
        return False


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
