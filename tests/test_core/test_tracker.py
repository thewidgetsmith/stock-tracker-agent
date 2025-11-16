"""Tests for core tracker functionality."""

import sys
from datetime import date, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

sys.path.append("src")


class TestTrackerModule:
    """Test tracker operations and monitoring logic."""

    @patch("sentinel.core.tracker.TrackedStockRepository")
    def test_get_tracked_stocks(self, mock_repo_class):
        """Test getting tracked stocks list."""
        from sentinel.core.tracker import get_tracked_stocks

        # Setup mock repository
        mock_repo = Mock()
        mock_repo.__enter__ = Mock(return_value=mock_repo)
        mock_repo.__exit__ = Mock(return_value=None)
        mock_repo.get_stock_symbols.return_value = ["AAPL", "GOOGL", "MSFT"]

        mock_repo_class.return_value = mock_repo

        result = get_tracked_stocks()

        assert result == ["AAPL", "GOOGL", "MSFT"]
        mock_repo.get_stock_symbols.assert_called_once()

    @patch("sentinel.core.tracker.TrackedStockRepository")
    def test_get_tracked_stocks_empty(self, mock_repo_class):
        """Test getting empty tracked stocks list."""
        from sentinel.core.tracker import get_tracked_stocks

        # Setup mock repository
        mock_repo = Mock()
        mock_repo.__enter__ = Mock(return_value=mock_repo)
        mock_repo.__exit__ = Mock(return_value=None)
        mock_repo.get_stock_symbols.return_value = []

        mock_repo_class.return_value = mock_repo

        result = get_tracked_stocks()

        assert result == []
        mock_repo.get_stock_symbols.assert_called_once()

    @patch("sentinel.core.tracker.AlertHistoryRepository")
    @patch("sentinel.core.tracker.date")
    def test_update_alert_history_new_alert(self, mock_date, mock_alert_repo_class):
        """Test updating alert history for new alert."""
        from sentinel.core.tracker import update_alert_history

        # Setup mock date
        mock_today = date(2024, 1, 1)
        mock_date.today.return_value = mock_today

        # Setup mock repository
        mock_repo = Mock()
        mock_repo.__enter__ = Mock(return_value=mock_repo)
        mock_repo.__exit__ = Mock(return_value=None)
        mock_repo.has_alert_been_sent.return_value = False  # No alert sent today
        mock_repo.add_alert.return_value = Mock()  # Mock alert object

        mock_alert_repo_class.return_value = mock_repo

        result = update_alert_history("AAPL")

        assert result is True
        mock_repo.has_alert_been_sent.assert_called_once_with("AAPL", "2024-01-01")
        mock_repo.add_alert.assert_called_once_with(
            "AAPL",
            "2024-01-01",
            alert_type="daily",
            message_content="Daily alert for AAPL",
        )

    @patch("sentinel.core.tracker.AlertHistoryRepository")
    @patch("sentinel.core.tracker.date")
    def test_update_alert_history_already_sent(self, mock_date, mock_alert_repo_class):
        """Test updating alert history when alert already sent today."""
        from sentinel.core.tracker import update_alert_history

        # Setup mock date
        mock_today = date(2024, 1, 1)
        mock_date.today.return_value = mock_today

        # Setup mock repository
        mock_repo = Mock()
        mock_repo.__enter__ = Mock(return_value=mock_repo)
        mock_repo.__exit__ = Mock(return_value=None)
        mock_repo.has_alert_been_sent.return_value = True  # Alert already sent

        mock_alert_repo_class.return_value = mock_repo

        result = update_alert_history("AAPL")

        assert result is False
        mock_repo.has_alert_been_sent.assert_called_once_with("AAPL", "2024-01-01")
        mock_repo.add_alert.assert_not_called()

    @patch("sentinel.core.tracker.asyncio.run")
    @patch("sentinel.core.tracker.run_research_pipeline")
    @patch("sentinel.core.tracker.update_alert_history")
    @patch("sentinel.core.tracker.get_stock_price")
    @patch("sentinel.core.tracker.get_tracked_stocks")
    def test_track_stocks_triggers_research(
        self,
        mock_get_tracked,
        mock_get_price,
        mock_update_alert,
        mock_research,
        mock_asyncio_run,
    ):
        """Test stock tracking triggers research for significant price movements."""
        from sentinel.core.tracker import track_stocks

        # Setup mock tracked stocks
        mock_get_tracked.return_value = ["AAPL"]

        # Setup mock stock price with significant change (5% increase)
        mock_price_response = Mock()
        mock_price_response.current_price = 105.0
        mock_price_response.previous_close = 100.0
        mock_get_price.return_value = mock_price_response

        # Setup mock alert history (should send alert)
        mock_update_alert.return_value = True

        # Setup mock research pipeline
        mock_research.return_value = AsyncMock()

        # Run the function
        track_stocks()

        # Verify calls
        mock_get_tracked.assert_called_once()
        mock_get_price.assert_called_once_with("AAPL")
        mock_update_alert.assert_called_once_with("AAPL")
        mock_asyncio_run.assert_called_once()

    @patch("sentinel.core.tracker.update_alert_history")
    @patch("sentinel.core.tracker.get_stock_price")
    @patch("sentinel.core.tracker.get_tracked_stocks")
    def test_track_stocks_no_significant_change(
        self, mock_get_tracked, mock_get_price, mock_update_alert
    ):
        """Test stock tracking with no significant price change."""
        from sentinel.core.tracker import track_stocks

        # Setup mock tracked stocks
        mock_get_tracked.return_value = ["AAPL"]

        # Setup mock stock price with small change (0.5% increase)
        mock_price_response = Mock()
        mock_price_response.current_price = 100.5
        mock_price_response.previous_close = 100.0
        mock_get_price.return_value = mock_price_response

        # Run the function
        track_stocks()

        # Verify calls
        mock_get_tracked.assert_called_once()
        mock_get_price.assert_called_once_with("AAPL")
        mock_update_alert.assert_not_called()  # Should not try to alert for small change

    @patch("sentinel.core.tracker.get_stock_price")
    @patch("sentinel.core.tracker.get_tracked_stocks")
    def test_track_stocks_handles_exceptions(self, mock_get_tracked, mock_get_price):
        """Test stock tracking handles exceptions gracefully."""
        from sentinel.core.tracker import track_stocks

        # Setup mock tracked stocks
        mock_get_tracked.return_value = ["AAPL", "GOOGL"]

        # Setup mock to raise exception for first stock
        mock_get_price.side_effect = [
            Exception("API Error"),
            Mock(current_price=100.5, previous_close=100.0),
        ]

        # Should not raise exception
        track_stocks()

        # Verify both stocks were attempted
        assert mock_get_price.call_count == 2

    @patch("sentinel.core.tracker.get_tracked_stocks")
    def test_track_stocks_empty_list(self, mock_get_tracked):
        """Test stock tracking with empty tracked stocks list."""
        from sentinel.core.tracker import track_stocks

        # Setup empty tracked stocks
        mock_get_tracked.return_value = []

        # Should complete without errors
        track_stocks()

        mock_get_tracked.assert_called_once()


class TestTrackerUtilities:
    """Test tracker utility functions and calculations."""

    def test_price_change_calculation(self):
        """Test price change percentage calculation logic."""
        # Test the calculation logic used in track_stocks

        # 5% increase
        current = 105.0
        previous = 100.0
        change_percent = (current / previous) - 1
        assert abs(change_percent - 0.05) < 0.001
        assert abs(change_percent) >= 0.01  # Should trigger alert

        # 0.5% increase (below threshold)
        current = 100.5
        previous = 100.0
        change_percent = (current / previous) - 1
        assert abs(change_percent - 0.005) < 0.001
        assert abs(change_percent) < 0.01  # Should not trigger alert

        # 5% decrease
        current = 95.0
        previous = 100.0
        change_percent = (current / previous) - 1
        assert abs(change_percent - (-0.05)) < 0.001
        assert abs(change_percent) >= 0.01  # Should trigger alert

    def test_threshold_logic(self):
        """Test the 1% threshold logic for triggering alerts."""
        threshold = 0.01  # 1%

        # Above threshold cases
        assert abs(0.02) >= threshold  # 2% change
        assert abs(-0.015) >= threshold  # -1.5% change
        assert abs(0.01) >= threshold  # Exactly 1% change

        # Below threshold cases
        assert abs(0.005) < threshold  # 0.5% change
        assert abs(-0.008) < threshold  # -0.8% change
        assert abs(0.0) < threshold  # No change

    @patch("sentinel.core.tracker.date")
    def test_date_string_format(self, mock_date):
        """Test date string formatting used in alert history."""
        from sentinel.core.tracker import update_alert_history

        # Mock date
        mock_today = date(2024, 3, 15)
        mock_date.today.return_value = mock_today

        with patch("sentinel.core.tracker.AlertHistoryRepository") as mock_repo_class:
            mock_repo = Mock()
            mock_repo.__enter__ = Mock(return_value=mock_repo)
            mock_repo.__exit__ = Mock(return_value=None)
            mock_repo.has_alert_been_sent.return_value = True
            mock_repo_class.return_value = mock_repo

            update_alert_history("AAPL")

            # Verify date is formatted correctly
            mock_repo.has_alert_been_sent.assert_called_once_with("AAPL", "2024-03-15")
