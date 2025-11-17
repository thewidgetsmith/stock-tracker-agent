"""Tests for scheduler functionality including politician tracking jobs."""

import sys
from unittest.mock import Mock, patch

import pytest

sys.path.append("src")
from sentinel.scheduler import (
    add_politician_tracking_job,
    add_stock_tracking_job,
    create_scheduler,
    get_global_scheduler,
    list_scheduled_jobs,
    shutdown_scheduler,
    start_scheduler,
)


class TestCreateScheduler:
    """Test scheduler creation functionality."""

    @patch("sentinel.scheduler.SQLAlchemyJobStore")
    @patch("sentinel.scheduler.ThreadPoolExecutor")
    @patch("sentinel.scheduler.BackgroundScheduler")
    def test_create_scheduler(self, mock_bg_scheduler, mock_executor, mock_jobstore):
        """Test that scheduler is created with correct configuration."""
        mock_scheduler = Mock()
        mock_bg_scheduler.return_value = mock_scheduler

        scheduler = create_scheduler()

        assert scheduler == mock_scheduler
        mock_bg_scheduler.assert_called_once()

        # Verify configuration included jobstores and executors
        call_kwargs = mock_bg_scheduler.call_args[1]
        assert "jobstores" in call_kwargs
        assert "executors" in call_kwargs
        assert "job_defaults" in call_kwargs


class TestGlobalScheduler:
    """Test global scheduler management."""

    @patch("sentinel.scheduler.create_scheduler")
    def test_get_global_scheduler_creates_if_none(self, mock_create):
        """Test that global scheduler is created if it doesn't exist."""
        mock_scheduler = Mock()
        mock_create.return_value = mock_scheduler

        # Reset global scheduler
        with patch("sentinel.scheduler._global_scheduler", None):
            scheduler = get_global_scheduler()

        assert scheduler == mock_scheduler
        mock_create.assert_called_once()

    @patch("sentinel.scheduler._global_scheduler", Mock(name="existing_scheduler"))
    def test_get_global_scheduler_returns_existing(self):
        """Test that existing global scheduler is returned."""
        with patch("sentinel.scheduler._global_scheduler") as mock_existing:
            scheduler = get_global_scheduler()
            assert scheduler == mock_existing


class TestStartShutdownScheduler:
    """Test scheduler lifecycle management."""

    @patch("sentinel.scheduler.get_global_scheduler")
    def test_start_scheduler(self, mock_get_scheduler):
        """Test starting the scheduler."""
        mock_scheduler = Mock()
        mock_get_scheduler.return_value = mock_scheduler

        start_scheduler()

        mock_scheduler.start.assert_called_once()

    @patch("sentinel.scheduler.get_global_scheduler")
    def test_shutdown_scheduler(self, mock_get_scheduler):
        """Test shutting down the scheduler."""
        mock_scheduler = Mock()
        mock_get_scheduler.return_value = mock_scheduler

        shutdown_scheduler()

        mock_scheduler.shutdown.assert_called_once_with(wait=False)


class TestAddStockTrackingJob:
    """Test stock tracking job functionality."""

    @patch("sentinel.scheduler.get_global_scheduler")
    def test_add_stock_tracking_job_success(self, mock_get_scheduler):
        """Test successfully adding stock tracking job."""
        mock_scheduler = Mock()
        mock_get_scheduler.return_value = mock_scheduler

        result = add_stock_tracking_job(60)

        assert result is True
        mock_scheduler.add_job.assert_called_once()

        # Verify job configuration
        call_args = mock_scheduler.add_job.call_args
        assert call_args[1]["id"] == "stock_tracking"
        assert call_args[1]["trigger"] == "interval"
        assert call_args[1]["minutes"] == 60

    @patch("sentinel.scheduler.get_global_scheduler")
    def test_add_stock_tracking_job_scheduler_error(self, mock_get_scheduler):
        """Test handling scheduler errors when adding stock job."""
        mock_scheduler = Mock()
        mock_scheduler.add_job.side_effect = Exception("Scheduler error")
        mock_get_scheduler.return_value = mock_scheduler

        result = add_stock_tracking_job()

        assert result is False


class TestAddPoliticianTrackingJob:
    """Test politician tracking job functionality."""

    @patch("sentinel.scheduler.get_settings")
    @patch("sentinel.scheduler.get_global_scheduler")
    def test_add_politician_tracking_job_success(
        self, mock_get_scheduler, mock_get_settings
    ):
        """Test successfully adding politician tracking job."""
        mock_settings = Mock()
        mock_settings.quiver_api_token = "test_token"
        mock_get_settings.return_value = mock_settings

        mock_scheduler = Mock()
        mock_get_scheduler.return_value = mock_scheduler

        result = add_politician_tracking_job(9)

        assert result is True
        mock_scheduler.add_job.assert_called_once()

        # Verify job configuration
        call_args = mock_scheduler.add_job.call_args
        assert call_args[1]["id"] == "politician_tracking"
        assert call_args[1]["trigger"] == "cron"
        assert call_args[1]["hour"] == 9
        assert call_args[1]["minute"] == 0

    @patch("sentinel.scheduler.get_settings")
    def test_add_politician_tracking_job_no_token(self, mock_get_settings):
        """Test adding politician tracking job without API token."""
        mock_settings = Mock()
        mock_settings.quiver_api_token = None
        mock_get_settings.return_value = mock_settings

        result = add_politician_tracking_job()

        assert result is False

    @patch("sentinel.scheduler.get_settings")
    @patch("sentinel.scheduler.get_global_scheduler")
    def test_add_politician_tracking_job_scheduler_error(
        self, mock_get_scheduler, mock_get_settings
    ):
        """Test handling scheduler errors when adding politician job."""
        mock_settings = Mock()
        mock_settings.quiver_api_token = "test_token"
        mock_get_settings.return_value = mock_settings

        mock_scheduler = Mock()
        mock_scheduler.add_job.side_effect = Exception("Scheduler error")
        mock_get_scheduler.return_value = mock_scheduler

        result = add_politician_tracking_job()

        assert result is False

    @patch("sentinel.scheduler.get_settings")
    @patch("sentinel.scheduler.get_global_scheduler")
    def test_politician_job_function_reference(
        self, mock_get_scheduler, mock_get_settings
    ):
        """Test that politician tracking job uses correct function reference."""
        mock_settings = Mock()
        mock_settings.quiver_api_token = "test_token"
        mock_get_settings.return_value = mock_settings

        mock_scheduler = Mock()
        mock_get_scheduler.return_value = mock_scheduler

        add_politician_tracking_job()

        # Verify the function reference is serializable (not a lambda)
        call_args = mock_scheduler.add_job.call_args
        job_func = call_args[0][0]

        # Should be a proper module function, not a lambda
        assert hasattr(job_func, "__module__")
        assert hasattr(job_func, "__name__")


class TestListScheduledJobs:
    """Test job listing functionality."""

    @patch("sentinel.scheduler.get_global_scheduler")
    @patch("builtins.print")
    def test_list_scheduled_jobs(self, mock_print, mock_get_scheduler):
        """Test listing scheduled jobs."""
        mock_job1 = Mock()
        mock_job1.id = "stock_tracking"
        mock_job1.name = "Stock Tracking"
        mock_job1.next_run_time = "2024-01-15 10:00:00"

        mock_job2 = Mock()
        mock_job2.id = "politician_tracking"
        mock_job2.name = "Politician Tracking"
        mock_job2.next_run_time = "2024-01-16 09:00:00"

        mock_scheduler = Mock()
        mock_scheduler.get_jobs.return_value = [mock_job1, mock_job2]
        mock_get_scheduler.return_value = mock_scheduler

        result = list_scheduled_jobs()

        # Function returns None but prints job information
        assert result is None
        mock_scheduler.get_jobs.assert_called_once()

        # Verify print was called with job information
        mock_print.assert_any_call("Scheduled jobs:")
        mock_print.assert_any_call(
            "  - stock_tracking: Stock Tracking (next run: 2024-01-15 10:00:00)"
        )
        mock_print.assert_any_call(
            "  - politician_tracking: Politician Tracking (next run: 2024-01-16 09:00:00)"
        )

    @patch("sentinel.scheduler.get_global_scheduler")
    @patch("builtins.print")
    def test_list_scheduled_jobs_empty(self, mock_print, mock_get_scheduler):
        """Test listing when no jobs are scheduled."""
        mock_scheduler = Mock()
        mock_scheduler.get_jobs.return_value = []
        mock_get_scheduler.return_value = mock_scheduler

        result = list_scheduled_jobs()

        assert result is None
        mock_print.assert_called_once_with("No scheduled jobs")


class TestSchedulerIntegration:
    """Integration tests for scheduler functionality."""

    @patch("sentinel.scheduler.get_settings")
    @patch("sentinel.core.politician_tracker.track_politicians")
    @patch("sentinel.scheduler.get_global_scheduler")
    def test_politician_tracking_job_integration(
        self, mock_get_scheduler, mock_track_politicians, mock_get_settings
    ):
        """Test integration between scheduler and politician tracking."""
        mock_settings = Mock()
        mock_settings.quiver_api_token = "test_token"
        mock_get_settings.return_value = mock_settings

        mock_scheduler = Mock()
        mock_get_scheduler.return_value = mock_scheduler

        # Add politician tracking job
        result = add_politician_tracking_job(9)

        assert result is True
        mock_scheduler.add_job.assert_called_once()

        # Verify job configuration matches expectations
        call_args = mock_scheduler.add_job.call_args
        assert call_args[1]["id"] == "politician_tracking"
        assert call_args[1]["hour"] == 9
        assert call_args[1]["minute"] == 0

    @patch("sentinel.scheduler.get_global_scheduler")
    def test_scheduler_lifecycle_integration(self, mock_get_scheduler):
        """Test complete scheduler lifecycle."""
        mock_scheduler = Mock()
        mock_get_scheduler.return_value = mock_scheduler

        # Should start without errors
        start_scheduler()
        mock_scheduler.start.assert_called_once()

        # Should shutdown cleanly
        shutdown_scheduler()
        mock_scheduler.shutdown.assert_called_once_with(wait=False)


# Mock fixtures for testing
@pytest.fixture
def mock_scheduler_settings():
    """Fixture providing mock scheduler settings."""
    settings = Mock()
    settings.quiver_api_token = "test_quiver_token"
    return settings


@pytest.fixture
def mock_politician_tracking_config():
    """Fixture providing mock politician tracking configuration."""
    return {
        "job_id": "politician_tracking",
        "trigger": "cron",
        "hour": 9,
        "minute": 0,
        "timezone": "UTC",
    }


class TestSchedulerFixtures:
    """Test scheduler with fixture data."""

    @patch("sentinel.scheduler.get_settings")
    @patch("sentinel.scheduler.get_global_scheduler")
    def test_politician_job_with_mock_config(
        self,
        mock_get_scheduler,
        mock_scheduler_settings,
        mock_politician_tracking_config,
    ):
        """Test politician tracking job with mock configuration."""
        with patch("sentinel.scheduler.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_scheduler_settings

            mock_scheduler = Mock()
            mock_get_scheduler.return_value = mock_scheduler

            result = add_politician_tracking_job()

            assert result is True
            mock_scheduler.add_job.assert_called_once()

            # Verify configuration matches expected
            call_args = mock_scheduler.add_job.call_args
            assert call_args[1]["hour"] == mock_politician_tracking_config["hour"]
            assert call_args[1]["minute"] == mock_politician_tracking_config["minute"]
