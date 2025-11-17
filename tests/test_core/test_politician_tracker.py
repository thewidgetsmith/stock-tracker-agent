"""Tests for politician tracking functionality."""

import asyncio
import sys
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

sys.path.append("src")
from sentinel.core.politician_tracker import (
    fetch_politician_trades,
    get_tracked_politicians,
    mark_activities_analyzed,
    run_politician_tracking_sync,
    should_trigger_research,
    track_politicians,
)


class TestGetTrackedPoliticians:
    """Test getting list of tracked politicians."""

    @patch("sentinel.core.politician_tracker.TrackedPoliticianRepository")
    def test_get_tracked_politicians_success(self, mock_repo_class):
        """Test successfully getting tracked politicians."""
        # Mock politician objects
        mock_politician1 = Mock()
        mock_politician1.name = "Nancy Pelosi"
        mock_politician2 = Mock()
        mock_politician2.name = "Kevin McCarthy"

        # Mock tracked politician objects
        mock_tracked1 = Mock()
        mock_tracked1.politician = mock_politician1
        mock_tracked2 = Mock()
        mock_tracked2.politician = mock_politician2

        # Mock repository
        mock_repo = Mock()
        mock_repo.get_all_tracked_politicians.return_value = [
            mock_tracked1,
            mock_tracked2,
        ]
        mock_repo_class.return_value.__enter__.return_value = mock_repo

        result = get_tracked_politicians()

        assert result == ["Nancy Pelosi", "Kevin McCarthy"]
        mock_repo.get_all_tracked_politicians.assert_called_once()

    @patch("sentinel.core.politician_tracker.TrackedPoliticianRepository")
    def test_get_tracked_politicians_empty(self, mock_repo_class):
        """Test getting tracked politicians when none exist."""
        mock_repo = Mock()
        mock_repo.get_all_tracked_politicians.return_value = []
        mock_repo_class.return_value.__enter__.return_value = mock_repo

        result = get_tracked_politicians()

        assert result == []
        mock_repo.get_all_tracked_politicians.assert_called_once()

    @patch("sentinel.core.politician_tracker.TrackedPoliticianRepository")
    def test_get_tracked_politicians_missing_politician(self, mock_repo_class):
        """Test getting tracked politicians when some have missing politician objects."""
        mock_politician = Mock()
        mock_politician.name = "Nancy Pelosi"

        mock_tracked1 = Mock()
        mock_tracked1.politician = mock_politician
        mock_tracked2 = Mock()
        mock_tracked2.politician = None  # Missing politician

        mock_repo = Mock()
        mock_repo.get_all_tracked_politicians.return_value = [
            mock_tracked1,
            mock_tracked2,
        ]
        mock_repo_class.return_value.__enter__.return_value = mock_repo

        result = get_tracked_politicians()

        assert result == ["Nancy Pelosi"]  # Only the valid one


class TestFetchPoliticianTrades:
    """Test fetching politician trades from Quiver API."""

    @patch("sentinel.core.politician_tracker.CongressionalService")
    @patch("sentinel.core.politician_tracker.get_settings")
    @pytest.mark.asyncio
    async def test_fetch_politician_trades_success(
        self, mock_get_settings, mock_service_class
    ):
        """Test successfully fetching politician trades."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.quiver_api_token = "test_token"
        mock_get_settings.return_value = mock_settings

        # Mock service
        mock_service = Mock()
        mock_service.get_congressional_trades = AsyncMock(
            return_value=[
                {
                    "politician": "Nancy Pelosi",
                    "ticker": "AAPL",
                    "amount": "50000-100000",
                }
            ]
        )
        mock_service_class.return_value = mock_service

        result = await fetch_politician_trades("Nancy Pelosi")

        assert result is True
        mock_service.get_congressional_trades.assert_called_once_with(
            representative="Nancy Pelosi", days_back=7, save_to_db=True
        )

    @patch("sentinel.core.politician_tracker.get_settings")
    @pytest.mark.asyncio
    async def test_fetch_politician_trades_no_token(self, mock_get_settings):
        """Test handling when no Quiver API token is configured."""
        mock_settings = Mock()
        mock_settings.quiver_api_token = None
        mock_get_settings.return_value = mock_settings

        result = await fetch_politician_trades("Nancy Pelosi")

        assert result is False

    @patch("sentinel.core.politician_tracker.CongressionalService")
    @patch("sentinel.core.politician_tracker.get_settings")
    @pytest.mark.asyncio
    async def test_fetch_politician_trades_no_trades_found(
        self, mock_get_settings, mock_service_class
    ):
        """Test when no trades are found."""
        mock_settings = Mock()
        mock_settings.quiver_api_token = "test_token"
        mock_get_settings.return_value = mock_settings

        mock_service = Mock()
        mock_service.get_congressional_trades = AsyncMock(return_value=[])
        mock_service_class.return_value = mock_service

        result = await fetch_politician_trades("Nancy Pelosi")

        assert result is False

    @patch("sentinel.core.politician_tracker.CongressionalService")
    @patch("sentinel.core.politician_tracker.get_settings")
    @pytest.mark.asyncio
    async def test_fetch_politician_trades_api_error(
        self, mock_get_settings, mock_service_class
    ):
        """Test handling API errors."""
        mock_settings = Mock()
        mock_settings.quiver_api_token = "test_token"
        mock_get_settings.return_value = mock_settings

        mock_service = Mock()
        mock_service.get_congressional_trades = AsyncMock(
            side_effect=Exception("API Error")
        )
        mock_service_class.return_value = mock_service

        result = await fetch_politician_trades("Nancy Pelosi")

        assert result is False


class TestShouldTriggerResearch:
    """Test logic for determining when to trigger research."""

    @patch("sentinel.core.politician_tracker.PoliticianActivityRepository")
    def test_should_trigger_research_with_unanalyzed_activities(self, mock_repo_class):
        """Test triggering research when there are unanalyzed activities."""
        # Mock activities
        mock_activity1 = Mock()
        mock_activity1.is_analyzed = False
        mock_activity2 = Mock()
        mock_activity2.is_analyzed = True

        mock_repo = Mock()
        mock_repo.get_recent_activities_by_politician.return_value = [
            mock_activity1,
            mock_activity2,
        ]
        mock_repo_class.return_value.__enter__.return_value = mock_repo

        result = should_trigger_research("Nancy Pelosi")

        assert result is True
        mock_repo.get_recent_activities_by_politician.assert_called_once_with(
            "Nancy Pelosi", days=2
        )

    @patch("sentinel.core.politician_tracker.PoliticianActivityRepository")
    def test_should_trigger_research_all_analyzed(self, mock_repo_class):
        """Test not triggering research when all activities are analyzed."""
        mock_activity = Mock()
        mock_activity.is_analyzed = True

        mock_repo = Mock()
        mock_repo.get_recent_activities_by_politician.return_value = [mock_activity]
        mock_repo_class.return_value.__enter__.return_value = mock_repo

        result = should_trigger_research("Nancy Pelosi")

        assert result is False

    @patch("sentinel.core.politician_tracker.PoliticianActivityRepository")
    def test_should_trigger_research_no_activities(self, mock_repo_class):
        """Test not triggering research when no activities exist."""
        mock_repo = Mock()
        mock_repo.get_recent_activities_by_politician.return_value = []
        mock_repo_class.return_value.__enter__.return_value = mock_repo

        result = should_trigger_research("Nancy Pelosi")

        assert result is False


class TestMarkActivitiesAnalyzed:
    """Test marking activities as analyzed."""

    @patch("sentinel.core.politician_tracker.PoliticianActivityRepository")
    @pytest.mark.asyncio
    async def test_mark_activities_analyzed_success(self, mock_repo_class):
        """Test successfully marking activities as analyzed."""
        # Mock activities
        mock_activity1 = Mock()
        mock_activity1.id = 1
        mock_activity1.is_analyzed = False
        mock_activity2 = Mock()
        mock_activity2.id = 2
        mock_activity2.is_analyzed = True

        mock_repo = Mock()
        mock_repo.get_recent_activities_by_politician.return_value = [
            mock_activity1,
            mock_activity2,
        ]
        mock_repo_class.return_value.__enter__.return_value = mock_repo

        await mark_activities_analyzed("Nancy Pelosi")

        # Should only mark the unanalyzed activity
        mock_repo.mark_activity_analyzed.assert_called_once()
        call_args = mock_repo.mark_activity_analyzed.call_args
        assert call_args[0][0] == 1  # activity ID
        assert "Analyzed on" in call_args[1]["analysis_notes"]

    @patch("sentinel.core.politician_tracker.PoliticianActivityRepository")
    @pytest.mark.asyncio
    async def test_mark_activities_analyzed_error_handling(self, mock_repo_class):
        """Test error handling in mark activities analyzed."""
        mock_repo = Mock()
        mock_repo.get_recent_activities_by_politician.side_effect = Exception(
            "DB Error"
        )
        mock_repo_class.return_value.__enter__.return_value = mock_repo

        # Should not raise an exception
        await mark_activities_analyzed("Nancy Pelosi")


class TestTrackPoliticians:
    """Test the main track_politicians function."""

    @patch("sentinel.core.politician_tracker.get_tracked_politicians")
    @patch("sentinel.core.politician_tracker.fetch_politician_trades")
    @patch("sentinel.core.politician_tracker.should_trigger_research")
    @patch("sentinel.core.politician_tracker.run_politician_research_pipeline")
    @patch("sentinel.core.politician_tracker.mark_activities_analyzed")
    @pytest.mark.asyncio
    async def test_track_politicians_full_cycle(
        self,
        mock_mark_analyzed,
        mock_research_pipeline,
        mock_should_research,
        mock_fetch_trades,
        mock_get_tracked,
    ):
        """Test full politician tracking cycle."""
        # Setup mocks
        mock_get_tracked.return_value = ["Nancy Pelosi", "Kevin McCarthy"]
        mock_fetch_trades.return_value = True
        mock_should_research.side_effect = [True, False]  # Research only for first
        mock_research_pipeline.return_value = "Research completed"
        mock_mark_analyzed.return_value = None

        await track_politicians()

        # Verify all functions were called correctly
        mock_get_tracked.assert_called_once()
        assert mock_fetch_trades.call_count == 2
        mock_fetch_trades.assert_any_call("Nancy Pelosi")
        mock_fetch_trades.assert_any_call("Kevin McCarthy")

        assert mock_should_research.call_count == 2
        mock_should_research.assert_any_call("Nancy Pelosi")
        mock_should_research.assert_any_call("Kevin McCarthy")

        # Research pipeline should only be called for Nancy Pelosi
        mock_research_pipeline.assert_called_once_with("Nancy Pelosi")
        mock_mark_analyzed.assert_called_once_with("Nancy Pelosi")

    @patch("sentinel.core.politician_tracker.get_tracked_politicians")
    @pytest.mark.asyncio
    async def test_track_politicians_no_politicians(self, mock_get_tracked):
        """Test tracking when no politicians are tracked."""
        mock_get_tracked.return_value = []

        await track_politicians()

        # Should exit early
        mock_get_tracked.assert_called_once()

    @patch("sentinel.core.politician_tracker.get_tracked_politicians")
    @patch("sentinel.core.politician_tracker.fetch_politician_trades")
    @pytest.mark.asyncio
    async def test_track_politicians_error_handling(
        self, mock_fetch_trades, mock_get_tracked
    ):
        """Test error handling in politician tracking."""
        mock_get_tracked.return_value = ["Nancy Pelosi"]
        mock_fetch_trades.side_effect = Exception("Fetch error")

        # Should not raise an exception
        await track_politicians()

        mock_fetch_trades.assert_called_once_with("Nancy Pelosi")


class TestRunPoliticianTrackingSync:
    """Test the synchronous wrapper function."""

    @patch("sentinel.core.politician_tracker.track_politicians")
    @patch("asyncio.new_event_loop")
    @patch("asyncio.set_event_loop")
    def test_run_politician_tracking_sync_success(
        self, mock_set_event_loop, mock_new_event_loop, mock_track_politicians
    ):
        """Test successful execution of sync wrapper."""
        mock_loop = Mock()
        mock_new_event_loop.return_value = mock_loop
        mock_track_politicians.return_value = asyncio.Future()
        mock_track_politicians.return_value.set_result(None)

        run_politician_tracking_sync()

        mock_new_event_loop.assert_called_once()
        mock_set_event_loop.assert_called_once_with(mock_loop)
        mock_loop.run_until_complete.assert_called_once()
        mock_loop.close.assert_called_once()

    @patch("sentinel.core.politician_tracker.track_politicians")
    @patch("asyncio.new_event_loop")
    @patch("asyncio.set_event_loop")
    def test_run_politician_tracking_sync_error(
        self, mock_set_event_loop, mock_new_event_loop, mock_track_politicians
    ):
        """Test error handling in sync wrapper."""
        mock_loop = Mock()
        mock_new_event_loop.return_value = mock_loop
        mock_loop.run_until_complete.side_effect = Exception("Sync error")

        # Should not raise an exception
        run_politician_tracking_sync()

        mock_loop.close.assert_called_once()


# Integration test fixtures
@pytest.fixture
def mock_politician_data():
    """Fixture providing mock politician data."""
    return {
        "politicians": ["Nancy Pelosi", "Kevin McCarthy"],
        "activities": [
            {
                "id": 1,
                "politician": "Nancy Pelosi",
                "ticker": "AAPL",
                "amount": "50000-100000",
                "is_analyzed": False,
                "date": date.today(),
            },
            {
                "id": 2,
                "politician": "Kevin McCarthy",
                "ticker": "MSFT",
                "amount": "15000-50000",
                "is_analyzed": True,
                "date": date.today(),
            },
        ],
    }


class TestPoliticianTrackingIntegration:
    """Integration tests for politician tracking."""

    @patch("sentinel.core.politician_tracker.get_tracked_politicians")
    @patch("sentinel.core.politician_tracker.fetch_politician_trades")
    @patch("sentinel.core.politician_tracker.should_trigger_research")
    @patch("sentinel.core.politician_tracker.run_politician_research_pipeline")
    @patch("sentinel.core.politician_tracker.mark_activities_analyzed")
    @pytest.mark.asyncio
    async def test_politician_tracking_integration(
        self,
        mock_mark_analyzed,
        mock_research_pipeline,
        mock_should_research,
        mock_fetch_trades,
        mock_get_tracked,
        mock_politician_data,
    ):
        """Test politician tracking integration with realistic data flow."""
        # Setup realistic scenario
        mock_get_tracked.return_value = mock_politician_data["politicians"]
        mock_fetch_trades.return_value = True
        mock_should_research.side_effect = [
            True,
            False,
        ]  # Nancy needs research, Kevin doesn't
        mock_research_pipeline.return_value = (
            "Analysis: Nancy Pelosi's AAPL trade shows..."
        )
        mock_mark_analyzed.return_value = None

        await track_politicians()

        # Verify the complete flow
        mock_get_tracked.assert_called_once()

        # Both politicians should have trades fetched
        assert mock_fetch_trades.call_count == 2

        # Both should be checked for research need
        assert mock_should_research.call_count == 2

        # Only Nancy should get research (has unanalyzed activities)
        mock_research_pipeline.assert_called_once_with("Nancy Pelosi")
        mock_mark_analyzed.assert_called_once_with("Nancy Pelosi")

    @pytest.mark.asyncio
    async def test_empty_politician_list_handling(self):
        """Test handling of empty politician list."""
        with patch(
            "sentinel.core.politician_tracker.get_tracked_politicians"
        ) as mock_get:
            mock_get.return_value = []

            # Should complete without error
            await track_politicians()

            mock_get.assert_called_once()
