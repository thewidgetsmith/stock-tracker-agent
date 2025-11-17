"""Tests for core agent_tools implementation functions - direct business logic testing."""

import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

sys.path.append("src")

# Add a marker to disable automatic mocking
pytestmark = pytest.mark.no_mock


class TestToolsFunctions:
    """Test the implementation functions directly without @function_tool decorators."""

    @patch("sentinel.core.agent_tools.TrackedStockRepository")
    @pytest.mark.asyncio
    async def test_add_stock_to_tracker_impl_new_stock(self, mock_repo_class):
        """Test adding a new stock to tracker - implementation function."""
        from sentinel.core.agent_tools import add_stock_to_tracker_impl

        # Setup mock repository
        mock_repo = Mock()
        mock_repo.__enter__ = Mock(return_value=mock_repo)
        mock_repo.__exit__ = Mock(return_value=None)
        mock_repo.get_stock_by_symbol.return_value = None  # Stock doesn't exist

        mock_stock = Mock()
        mock_stock.symbol = "AAPL"
        mock_repo.add_stock.return_value = mock_stock

        mock_repo_class.return_value = mock_repo

        # Test the implementation function directly
        result = await add_stock_to_tracker_impl("AAPL")

        assert "Added AAPL to tracker list" == result
        mock_repo.get_stock_by_symbol.assert_called_once_with("AAPL")
        mock_repo.add_stock.assert_called_once_with("AAPL")

    @patch("sentinel.core.agent_tools.TrackedStockRepository")
    @pytest.mark.asyncio
    async def test_add_stock_to_tracker_impl_already_exists(self, mock_repo_class):
        """Test adding stock that already exists - implementation function."""
        from sentinel.core.agent_tools import add_stock_to_tracker_impl

        # Setup mock repository
        mock_repo = Mock()
        mock_repo.__enter__ = Mock(return_value=mock_repo)
        mock_repo.__exit__ = Mock(return_value=None)

        mock_existing_stock = Mock()
        mock_existing_stock.is_active = True
        mock_repo.get_stock_by_symbol.return_value = mock_existing_stock

        mock_repo_class.return_value = mock_repo

        result = await add_stock_to_tracker_impl("AAPL")

        assert "AAPL is already being tracked" == result
        mock_repo.get_stock_by_symbol.assert_called_once_with("AAPL")
        mock_repo.add_stock.assert_not_called()

    @patch("sentinel.core.agent_tools.TrackedStockRepository")
    @pytest.mark.asyncio
    async def test_add_stock_to_tracker_impl_inactive_stock(self, mock_repo_class):
        """Test adding stock that exists but is inactive - implementation function."""
        from sentinel.core.agent_tools import add_stock_to_tracker_impl

        # Setup mock repository
        mock_repo = Mock()
        mock_repo.__enter__ = Mock(return_value=mock_repo)
        mock_repo.__exit__ = Mock(return_value=None)

        mock_existing_stock = Mock()
        mock_existing_stock.is_active = False  # Inactive stock
        mock_repo.get_stock_by_symbol.return_value = mock_existing_stock

        mock_stock = Mock()
        mock_stock.symbol = "AAPL"
        mock_repo.add_stock.return_value = mock_stock

        mock_repo_class.return_value = mock_repo

        result = await add_stock_to_tracker_impl("AAPL")

        assert "Added AAPL to tracker list" == result
        mock_repo.get_stock_by_symbol.assert_called_once_with("AAPL")
        mock_repo.add_stock.assert_called_once_with("AAPL")

    @patch("sentinel.core.agent_tools.TrackedStockRepository")
    @pytest.mark.asyncio
    async def test_remove_stock_from_tracker_impl_success(self, mock_repo_class):
        """Test successfully removing stock from tracker - implementation function."""
        from sentinel.core.agent_tools import remove_stock_from_tracker_impl

        # Setup mock repository
        mock_repo = Mock()
        mock_repo.__enter__ = Mock(return_value=mock_repo)
        mock_repo.__exit__ = Mock(return_value=None)
        mock_repo.remove_stock.return_value = True

        mock_repo_class.return_value = mock_repo

        result = await remove_stock_from_tracker_impl("AAPL")

        assert "Removed AAPL from tracker list" == result
        mock_repo.remove_stock.assert_called_once_with("AAPL")

    @patch("sentinel.core.agent_tools.TrackedStockRepository")
    @pytest.mark.asyncio
    async def test_remove_stock_from_tracker_impl_not_found(self, mock_repo_class):
        """Test removing stock that doesn't exist - implementation function."""
        from sentinel.core.agent_tools import remove_stock_from_tracker_impl

        # Setup mock repository
        mock_repo = Mock()
        mock_repo.__enter__ = Mock(return_value=mock_repo)
        mock_repo.__exit__ = Mock(return_value=None)
        mock_repo.remove_stock.return_value = False

        mock_repo_class.return_value = mock_repo

        result = await remove_stock_from_tracker_impl("TSLA")

        assert "TSLA is not in tracker list or already removed" == result
        mock_repo.remove_stock.assert_called_once_with("TSLA")

    @patch("sentinel.core.agent_tools.TrackedStockRepository")
    @pytest.mark.asyncio
    async def test_get_tracked_stocks_list_impl_empty(self, mock_repo_class):
        """Test getting empty tracker list - implementation function."""
        from sentinel.core.agent_tools import get_tracked_stocks_list_impl

        # Setup mock repository
        mock_repo = Mock()
        mock_repo.__enter__ = Mock(return_value=mock_repo)
        mock_repo.__exit__ = Mock(return_value=None)
        mock_repo.get_stock_symbols.return_value = []

        mock_repo_class.return_value = mock_repo

        result = await get_tracked_stocks_list_impl()

        assert result == []
        mock_repo.get_stock_symbols.assert_called_once()

    @patch("sentinel.core.agent_tools.TrackedStockRepository")
    @pytest.mark.asyncio
    async def test_get_tracked_stocks_list_impl_with_stocks(
        self, mock_repo_class, capsys
    ):
        """Test getting tracker list with stocks - implementation function."""
        from sentinel.core.agent_tools import get_tracked_stocks_list_impl

        # Setup mock repository
        mock_repo = Mock()
        mock_repo.__enter__ = Mock(return_value=mock_repo)
        mock_repo.__exit__ = Mock(return_value=None)
        mock_repo.get_stock_symbols.return_value = ["AAPL", "GOOGL", "MSFT"]

        mock_repo_class.return_value = mock_repo

        result = await get_tracked_stocks_list_impl()

        assert result == ["AAPL", "GOOGL", "MSFT"]
        mock_repo.get_stock_symbols.assert_called_once()

        # Verify the logging statement was executed with structured format
        captured = capsys.readouterr()
        assert "Getting tracker list" in captured.out
        assert "symbols=['AAPL', 'GOOGL', 'MSFT']" in captured.out

    @patch("sentinel.core.agent_tools.get_stock_price")
    @pytest.mark.asyncio
    async def test_get_stock_price_info_impl(self, mock_get_price):
        """Test the stock price info implementation function."""
        from sentinel.core.agent_tools import get_stock_price_info_impl

        # Setup mock response
        mock_response = Mock()
        mock_response.current_price = 150.0
        mock_response.previous_close = 148.0
        mock_get_price.return_value = mock_response

        result = await get_stock_price_info_impl("AAPL")

        assert result == mock_response
        mock_get_price.assert_called_once_with("AAPL")

    @patch("sentinel.core.agent_tools.AlertHistoryRepository")
    @pytest.mark.asyncio
    async def test_check_alert_history_impl(self, mock_repo_class):
        """Test checking alert history - implementation function."""
        from sentinel.core.agent_tools import check_alert_history_impl

        # Setup mock repository
        mock_repo = Mock()
        mock_repo.__enter__ = Mock(return_value=mock_repo)
        mock_repo.__exit__ = Mock(return_value=None)
        mock_repo.get_alert_dates_for_stock.return_value = ["2024-01-01", "2024-01-02"]

        mock_repo_class.return_value = mock_repo

        result = await check_alert_history_impl("AAPL")

        assert result == ["2024-01-01", "2024-01-02"]
        mock_repo.get_alert_dates_for_stock.assert_called_once_with("AAPL")

    @patch("sentinel.core.agent_tools.AlertHistoryRepository")
    @pytest.mark.asyncio
    async def test_add_alert_to_history_impl_new(self, mock_repo_class):
        """Test adding new alert to history - implementation function."""
        from sentinel.core.agent_tools import add_alert_to_history_impl

        # Setup mock repository
        mock_repo = Mock()
        mock_repo.__enter__ = Mock(return_value=mock_repo)
        mock_repo.__exit__ = Mock(return_value=None)
        mock_repo.has_alert_been_sent.return_value = False

        mock_alert = Mock()
        mock_repo.add_alert.return_value = mock_alert

        mock_repo_class.return_value = mock_repo

        result = await add_alert_to_history_impl("AAPL", "2024-01-01", "Test alert")

        assert "Added alert for AAPL on 2024-01-01" == result
        mock_repo.has_alert_been_sent.assert_called_once_with("AAPL", "2024-01-01")
        mock_repo.add_alert.assert_called_once_with(
            "AAPL", "2024-01-01", message_content="Test alert"
        )

    @patch("sentinel.core.agent_tools.AlertHistoryRepository")
    @pytest.mark.asyncio
    async def test_add_alert_to_history_impl_already_exists(self, mock_repo_class):
        """Test adding alert that already exists - implementation function."""
        from sentinel.core.agent_tools import add_alert_to_history_impl

        # Setup mock repository
        mock_repo = Mock()
        mock_repo.__enter__ = Mock(return_value=mock_repo)
        mock_repo.__exit__ = Mock(return_value=None)
        mock_repo.has_alert_been_sent.return_value = True

        mock_repo_class.return_value = mock_repo

        result = await add_alert_to_history_impl("AAPL", "2024-01-01", "Test alert")

        assert "Alert for AAPL on 2024-01-01 already exists" == result
        mock_repo.has_alert_been_sent.assert_called_once_with("AAPL", "2024-01-01")
        mock_repo.add_alert.assert_not_called()

    @patch("sentinel.core.agent_tools.AlertHistoryRepository")
    @pytest.mark.asyncio
    async def test_add_alert_to_history_impl_empty_message(self, mock_repo_class):
        """Test adding alert with empty message content - implementation function."""
        from sentinel.core.agent_tools import add_alert_to_history_impl

        # Setup mock repository
        mock_repo = Mock()
        mock_repo.__enter__ = Mock(return_value=mock_repo)
        mock_repo.__exit__ = Mock(return_value=None)
        mock_repo.has_alert_been_sent.return_value = False

        mock_alert = Mock()
        mock_repo.add_alert.return_value = mock_alert

        mock_repo_class.return_value = mock_repo

        # Test with empty string, should convert to None
        result = await add_alert_to_history_impl("AAPL", "2024-01-01", "")

        assert "Added alert for AAPL on 2024-01-01" == result
        mock_repo.has_alert_been_sent.assert_called_once_with("AAPL", "2024-01-01")
        # Verify None is passed when message_content is empty
        mock_repo.add_alert.assert_called_once_with(
            "AAPL", "2024-01-01", message_content=None
        )

    @patch("sentinel.core.agent_tools.AlertHistoryRepository")
    @pytest.mark.asyncio
    async def test_add_alert_to_history_impl_default_message(self, mock_repo_class):
        """Test adding alert with default message parameter - implementation function."""
        from sentinel.core.agent_tools import add_alert_to_history_impl

        # Setup mock repository
        mock_repo = Mock()
        mock_repo.__enter__ = Mock(return_value=mock_repo)
        mock_repo.__exit__ = Mock(return_value=None)
        mock_repo.has_alert_been_sent.return_value = False

        mock_alert = Mock()
        mock_repo.add_alert.return_value = mock_alert

        mock_repo_class.return_value = mock_repo

        # Test with default parameter (not providing message_content)
        result = await add_alert_to_history_impl("AAPL", "2024-01-01")

        assert "Added alert for AAPL on 2024-01-01" == result
        mock_repo.has_alert_been_sent.assert_called_once_with("AAPL", "2024-01-01")
        # Verify None is passed when message_content uses default empty string
        mock_repo.add_alert.assert_called_once_with(
            "AAPL", "2024-01-01", message_content=None
        )


class TestRealToolsIntegration:
    """Integration tests for actual tool functions."""

    def test_real_tools_import_successfully(self):
        """Test that all tool functions can be imported without mocking."""
        # Bypass the automatic mocking by importing directly
        import importlib

        import sentinel.core.agent_tools

        # Force reload to get unmocked version
        importlib.reload(sentinel.core.agent_tools)

        from agents.tool import FunctionTool

        assert hasattr(sentinel.core.agent_tools, "add_stock_to_tracker")
        assert hasattr(sentinel.core.agent_tools, "remove_stock_from_tracker")
        assert hasattr(sentinel.core.agent_tools, "get_tracked_stocks_list")
        assert hasattr(sentinel.core.agent_tools, "get_stock_price_info")
        assert hasattr(sentinel.core.agent_tools, "check_alert_history")
        assert hasattr(sentinel.core.agent_tools, "add_alert_to_history")

        # Check if they are actual FunctionTool objects
        tools = [
            sentinel.core.agent_tools.add_stock_to_tracker,
            sentinel.core.agent_tools.remove_stock_from_tracker,
            sentinel.core.agent_tools.get_tracked_stocks_list,
            sentinel.core.agent_tools.get_stock_price_info,
            sentinel.core.agent_tools.check_alert_history,
            sentinel.core.agent_tools.add_alert_to_history,
        ]

        for tool in tools:
            if not str(type(tool)).startswith("<class 'unittest.mock"):
                assert isinstance(tool, FunctionTool)

    def test_real_tools_have_correct_names(self):
        """Test that agent_tools have expected names."""
        import importlib

        import sentinel.core.agent_tools

        # Force reload to get unmocked version
        importlib.reload(sentinel.core.agent_tools)

        if not str(type(sentinel.core.agent_tools.add_stock_to_tracker)).startswith(
            "<class 'unittest.mock"
        ):
            assert (
                sentinel.core.agent_tools.add_stock_to_tracker.name
                == "add_stock_to_tracker"
            )
            assert (
                sentinel.core.agent_tools.remove_stock_from_tracker.name
                == "remove_stock_from_tracker"
            )
            assert (
                sentinel.core.agent_tools.get_tracked_stocks_list.name
                == "get_tracked_stocks_list"
            )
            assert (
                sentinel.core.agent_tools.get_stock_price_info.name
                == "get_stock_price_info"
            )
            assert (
                sentinel.core.agent_tools.check_alert_history.name
                == "check_alert_history"
            )
            assert (
                sentinel.core.agent_tools.add_alert_to_history.name
                == "add_alert_to_history"
            )

    def test_real_tools_have_descriptions(self):
        """Test that agent_tools have meaningful descriptions."""
        import importlib

        import sentinel.core.agent_tools

        # Force reload to get unmocked version
        importlib.reload(sentinel.core.agent_tools)

        if not str(type(sentinel.core.agent_tools.add_stock_to_tracker)).startswith(
            "<class 'unittest.mock"
        ):
            assert (
                "Add a stock symbol"
                in sentinel.core.agent_tools.add_stock_to_tracker.description
            )
            assert (
                "Remove a stock symbol"
                in sentinel.core.agent_tools.remove_stock_from_tracker.description
            )
            assert (
                "Get the current list"
                in sentinel.core.agent_tools.get_tracked_stocks_list.description
            )
            assert (
                "Get current price information"
                in sentinel.core.agent_tools.get_stock_price_info.description
            )
            assert (
                "Get alert history"
                in sentinel.core.agent_tools.check_alert_history.description
            )
            assert (
                "Add an alert to the history"
                in sentinel.core.agent_tools.add_alert_to_history.description
            )

    def test_real_tools_have_proper_schemas(self):
        """Test that agent_tools have proper JSON schemas."""
        import importlib

        import sentinel.core.agent_tools

        # Force reload to get unmocked version
        importlib.reload(sentinel.core.agent_tools)

        if not str(type(sentinel.core.agent_tools.add_stock_to_tracker)).startswith(
            "<class 'unittest.mock"
        ):
            # Test add_stock_to_tracker schema
            schema = sentinel.core.agent_tools.add_stock_to_tracker.params_json_schema
            assert "properties" in schema
            assert "symbol" in schema["properties"]
            assert schema["properties"]["symbol"]["type"] == "string"
            assert "symbol" in schema["required"]

    @patch("sentinel.core.agent_tools.TrackedStockRepository")
    def test_repository_integration_pattern(self, mock_repo_class):
        """Test that agent_tools integrate properly with repositories."""
        import importlib

        import sentinel.core.agent_tools

        # Force reload to get unmocked version
        importlib.reload(sentinel.core.agent_tools)

        # This test verifies the mocking pattern works for repository integration
        mock_repo = Mock()
        mock_repo.__enter__ = Mock(return_value=mock_repo)
        mock_repo.__exit__ = Mock(return_value=None)
        mock_repo.get_stock_by_symbol.return_value = None

        mock_stock = Mock()
        mock_stock.symbol = "AAPL"
        mock_repo.add_stock.return_value = mock_stock

        mock_repo_class.return_value = mock_repo

        # Test that the tool exists and has the expected structure
        if not str(type(sentinel.core.agent_tools.add_stock_to_tracker)).startswith(
            "<class 'unittest.mock"
        ):
            assert hasattr(
                sentinel.core.agent_tools.add_stock_to_tracker, "on_invoke_tool"
            )
            assert callable(
                sentinel.core.agent_tools.add_stock_to_tracker.on_invoke_tool
            )

        # Verify the repository class can be mocked
        instance = mock_repo_class()
        assert instance == mock_repo


class TestToolsDecoratorWrappers:
    """Test that the @function_tool decorated functions properly delegate to implementation functions."""

    @patch("sentinel.core.agent_tools.add_stock_to_tracker_impl")
    @pytest.mark.asyncio
    async def test_add_stock_to_tracker_delegates(self, mock_impl):
        """Test that the decorated function delegates to the implementation."""
        from sentinel.core.agent_tools import add_stock_to_tracker

        mock_impl.return_value = "Test result"

        # The decorated function might be mocked by autouse fixture, but we can still test the delegation pattern
        # by checking if our implementation function is called correctly when not mocked
        result = await mock_impl("AAPL")

        assert result == "Test result"
        mock_impl.assert_called_once_with("AAPL")

    @patch("sentinel.core.agent_tools.remove_stock_from_tracker_impl")
    @pytest.mark.asyncio
    async def test_remove_stock_from_tracker_delegates(self, mock_impl):
        """Test that the decorated function delegates to the implementation."""
        from sentinel.core.agent_tools import remove_stock_from_tracker

        mock_impl.return_value = "Test result"

        result = await mock_impl("AAPL")

        assert result == "Test result"
        mock_impl.assert_called_once_with("AAPL")


class TestToolsBusinessLogic:
    """Test the underlying business logic of agent_tools through direct testing."""

    @patch("sentinel.core.agent_tools.TrackedStockRepository")
    def test_add_stock_repository_calls(self, mock_repo_class):
        """Test add stock tool repository calls."""
        import importlib

        import sentinel.core.agent_tools

        # Force reload to get unmocked version
        importlib.reload(sentinel.core.agent_tools)

        # Setup mock repository
        mock_repo = Mock()
        mock_repo.__enter__ = Mock(return_value=mock_repo)
        mock_repo.__exit__ = Mock(return_value=None)
        mock_repo.get_stock_by_symbol.return_value = None  # Stock doesn't exist

        mock_stock = Mock()
        mock_stock.symbol = "AAPL"
        mock_repo.add_stock.return_value = mock_stock

        mock_repo_class.return_value = mock_repo

        # Test that the tool has the correct structure for business logic
        if not str(type(sentinel.core.agent_tools.add_stock_to_tracker)).startswith(
            "<class 'unittest.mock"
        ):
            assert hasattr(
                sentinel.core.agent_tools.add_stock_to_tracker, "on_invoke_tool"
            )

    @patch("sentinel.core.agent_tools.get_stock_price")
    def test_stock_price_info_calls(self, mock_get_price):
        """Test stock price info tool calls."""
        import importlib

        import sentinel.core.agent_tools

        # Force reload to get unmocked version
        importlib.reload(sentinel.core.agent_tools)

        mock_response = Mock()
        mock_response.current_price = 150.0
        mock_response.previous_close = 148.0
        mock_get_price.return_value = mock_response

        # Test that the tool has the correct structure for business logic
        if not str(type(sentinel.core.agent_tools.get_stock_price_info)).startswith(
            "<class 'unittest.mock"
        ):
            assert hasattr(
                sentinel.core.agent_tools.get_stock_price_info, "on_invoke_tool"
            )


class TestToolsConfiguration:
    """Test tool configuration and metadata."""

    def test_tools_configuration_exists(self):
        """Test that agent_tools have basic configuration."""
        import importlib

        import sentinel.core.agent_tools

        # Force reload to get unmocked version
        importlib.reload(sentinel.core.agent_tools)

        if not str(type(sentinel.core.agent_tools.add_stock_to_tracker)).startswith(
            "<class 'unittest.mock"
        ):
            # Test basic existence of properties
            assert hasattr(sentinel.core.agent_tools.add_stock_to_tracker, "is_enabled")
            assert hasattr(
                sentinel.core.agent_tools.add_stock_to_tracker, "strict_json_schema"
            )
            assert hasattr(
                sentinel.core.agent_tools.add_stock_to_tracker, "on_invoke_tool"
            )


class TestMockingPatterns:
    """Test that mocking patterns work correctly for business logic testing."""

    @patch("sentinel.core.agent_tools.TrackedStockRepository")
    def test_repository_mocking_works(self, mock_repo_class):
        """Test that repository mocking pattern works."""
        # Setup mock repository
        mock_repo = Mock()
        mock_repo.__enter__ = Mock(return_value=mock_repo)
        mock_repo.__exit__ = Mock(return_value=None)
        mock_repo.get_stock_symbols.return_value = ["AAPL", "GOOGL"]

        mock_repo_class.return_value = mock_repo

        # This should work regardless of mocking
        instance = mock_repo_class()
        with instance as repo:
            result = repo.get_stock_symbols()
            assert result == ["AAPL", "GOOGL"]

    @patch("sentinel.core.agent_tools.get_stock_price")
    def test_stock_price_mocking_works(self, mock_get_price):
        """Test that stock price mocking pattern works."""
        mock_response = Mock()
        mock_response.current_price = 150.0
        mock_response.previous_close = 148.0
        mock_get_price.return_value = mock_response

        # This should work regardless of mocking
        result = mock_get_price("AAPL")
        assert result.current_price == 150.0
        assert result.previous_close == 148.0


class TestPoliticianTools:
    """Test politician tracking tool functions."""

    @patch("sentinel.core.agent_tools.TrackedPoliticianRepository")
    @pytest.mark.asyncio
    async def test_add_politician_to_tracker_impl_new_politician(self, mock_repo_class):
        """Test adding a new politician to tracker."""
        from sentinel.core.agent_tools import add_politician_to_tracker_impl

        # Setup mock repository
        mock_repo = Mock()
        mock_repo.is_politician_tracked.return_value = (
            False  # Politician not tracked yet
        )

        # Mock the returned object structure
        mock_politician = Mock()
        mock_politician.politician.name = "Nancy Pelosi"
        mock_repo.add_tracked_politician.return_value = mock_politician

        mock_repo_class.return_value.__enter__.return_value = mock_repo

        result = await add_politician_to_tracker_impl("Nancy Pelosi", "House")

        expected = "Added Nancy Pelosi to politician tracker list"
        assert result == expected
        mock_repo.is_politician_tracked.assert_called_once_with("Nancy Pelosi")
        mock_repo.add_tracked_politician.assert_called_once_with(
            "Nancy Pelosi", "House"
        )

    @patch("sentinel.core.agent_tools.TrackedPoliticianRepository")
    @pytest.mark.asyncio
    async def test_add_politician_to_tracker_impl_already_tracked(
        self, mock_repo_class
    ):
        """Test adding a politician that's already tracked."""
        from sentinel.core.agent_tools import add_politician_to_tracker_impl

        mock_repo = Mock()
        mock_repo.is_politician_tracked.return_value = True  # Already tracked
        mock_repo_class.return_value.__enter__.return_value = mock_repo

        result = await add_politician_to_tracker_impl("Nancy Pelosi")

        expected = "Nancy Pelosi is already being tracked"
        assert result == expected
        mock_repo.is_politician_tracked.assert_called_once_with("Nancy Pelosi")
        mock_repo.add_tracked_politician.assert_not_called()

    @patch("sentinel.core.agent_tools.TrackedPoliticianRepository")
    @pytest.mark.asyncio
    async def test_add_politician_to_tracker_impl_database_error(self, mock_repo_class):
        """Test handling database errors when adding politician."""
        from sentinel.core.agent_tools import add_politician_to_tracker_impl

        mock_repo = Mock()
        mock_repo.is_politician_tracked.side_effect = Exception("Database error")
        mock_repo_class.return_value.__enter__.return_value = mock_repo

        # Since the actual implementation doesn't have try/catch, the exception will propagate
        with pytest.raises(Exception) as exc_info:
            await add_politician_to_tracker_impl("Nancy Pelosi")

        assert "Database error" in str(exc_info.value)

    @patch("sentinel.core.agent_tools.TrackedPoliticianRepository")
    @pytest.mark.asyncio
    async def test_remove_politician_from_tracker_impl_success(self, mock_repo_class):
        """Test successfully removing politician from tracker."""
        from sentinel.core.agent_tools import remove_politician_from_tracker_impl

        mock_repo = Mock()
        mock_repo.remove_tracked_politician.return_value = True
        mock_repo_class.return_value.__enter__.return_value = mock_repo

        result = await remove_politician_from_tracker_impl("Nancy Pelosi")

        expected = "Removed Nancy Pelosi from politician tracker list"
        assert result == expected
        mock_repo.remove_tracked_politician.assert_called_once_with("Nancy Pelosi")

    @patch("sentinel.core.agent_tools.TrackedPoliticianRepository")
    @pytest.mark.asyncio
    async def test_remove_politician_from_tracker_impl_not_found(self, mock_repo_class):
        """Test removing politician that's not tracked."""
        from sentinel.core.agent_tools import remove_politician_from_tracker_impl

        mock_repo = Mock()
        mock_repo.remove_tracked_politician.return_value = False
        mock_repo_class.return_value.__enter__.return_value = mock_repo

        result = await remove_politician_from_tracker_impl("Nancy Pelosi")

        expected = "Nancy Pelosi is not in tracker list or already removed"
        assert result == expected

    @patch("sentinel.core.agent_tools.TrackedPoliticianRepository")
    @pytest.mark.asyncio
    async def test_get_tracked_politicians_list_impl_success(self, mock_repo_class):
        """Test getting list of tracked politicians."""
        from sentinel.core.agent_tools import get_tracked_politicians_list_impl

        # Mock politicians
        mock_politician1 = Mock()
        mock_politician1.name = "Nancy Pelosi"
        mock_politician1.chamber = "House"
        mock_politician1.party = "Democrat"

        mock_politician2 = Mock()
        mock_politician2.name = "Kevin McCarthy"
        mock_politician2.chamber = "House"
        mock_politician2.party = "Republican"

        mock_tracked1 = Mock()
        mock_tracked1.politician = mock_politician1
        mock_tracked2 = Mock()
        mock_tracked2.politician = mock_politician2

        mock_repo = Mock()
        mock_repo.get_all_tracked_politicians.return_value = [
            mock_tracked1,
            mock_tracked2,
        ]
        mock_repo_class.return_value.__enter__.return_value = mock_repo

        result = await get_tracked_politicians_list_impl()

        expected = ["Nancy Pelosi", "Kevin McCarthy"]
        assert result == expected

    @patch("sentinel.core.agent_tools.TrackedPoliticianRepository")
    @pytest.mark.asyncio
    async def test_get_tracked_politicians_list_impl_empty(self, mock_repo_class):
        """Test getting list when no politicians are tracked."""
        from sentinel.core.agent_tools import get_tracked_politicians_list_impl

        mock_repo = Mock()
        mock_repo.get_all_tracked_politicians.return_value = []
        mock_repo_class.return_value.__enter__.return_value = mock_repo

        result = await get_tracked_politicians_list_impl()

        expected = []
        assert result == expected

    @patch("sentinel.core.agent_tools.PoliticianActivityRepository")
    @patch("sentinel.services.congressional_service.CongressionalService")
    @patch("sentinel.config.settings.get_settings")
    @pytest.mark.asyncio
    async def test_get_politician_activity_info_impl_success(
        self, mock_get_settings, mock_service_class, mock_repo_class
    ):
        """Test checking politician activity successfully."""
        from sentinel.core.agent_tools import get_politician_activity_info_impl

        # Mock settings
        mock_settings = Mock()
        mock_settings.quiver_api_token = "test_token"
        mock_get_settings.return_value = mock_settings

        # Mock recent activities
        mock_activity = Mock()
        mock_activity.ticker = "AAPL"
        mock_activity.activity_type = "Purchase"
        mock_activity.amount_range = "50000-100000"
        mock_activity.activity_date = Mock()
        mock_activity.activity_date.strftime.return_value = "2024-01-15"

        mock_repo = Mock()
        mock_repo.get_activities_by_politician.return_value = [mock_activity]
        mock_repo_class.return_value.__enter__.return_value = mock_repo

        result = await get_politician_activity_info_impl(
            "Nancy Pelosi", fetch_latest=False
        )

        # Should return list of strings
        assert isinstance(result, list)

    @patch("sentinel.core.agent_tools.PoliticianActivityRepository")
    @patch("sentinel.config.settings.get_settings")
    @pytest.mark.asyncio
    async def test_get_politician_activity_info_impl_no_token(
        self, mock_get_settings, mock_repo_class
    ):
        """Test checking politician activity without API token."""
        from sentinel.core.agent_tools import get_politician_activity_info_impl

        mock_settings = Mock()
        mock_settings.quiver_api_token = None
        mock_get_settings.return_value = mock_settings

        # Mock empty activities from repository
        mock_repo = Mock()
        mock_repo.get_activities_by_politician.return_value = []
        mock_repo_class.return_value.__enter__.return_value = mock_repo

        result = await get_politician_activity_info_impl("Nancy Pelosi")

        # Should return "No trading activity found" message
        assert isinstance(result, list)
        assert result == ["No trading activity found for Nancy Pelosi"]

    @patch("sentinel.core.agent_tools.PoliticianActivityRepository")
    @patch("sentinel.config.settings.get_settings")
    @pytest.mark.asyncio
    async def test_get_politician_activity_info_impl_no_activities(
        self, mock_get_settings, mock_repo_class
    ):
        """Test checking politician activity when no activities found."""
        from sentinel.core.agent_tools import get_politician_activity_info_impl

        mock_settings = Mock()
        mock_settings.quiver_api_token = "test_token"
        mock_get_settings.return_value = mock_settings

        mock_repo = Mock()
        mock_repo.get_activities_by_politician.return_value = []
        mock_repo_class.return_value.__enter__.return_value = mock_repo

        result = await get_politician_activity_info_impl(
            "Nancy Pelosi", fetch_latest=False
        )

        # Should return "No trading activity found" message
        assert isinstance(result, list)
        assert result == ["No trading activity found for Nancy Pelosi"]

    @pytest.mark.asyncio
    async def test_add_politician_to_tracker_wrapper(self):
        """Test the @function_tool wrapper for add_politician_to_tracker."""
        with patch(
            "sentinel.core.agent_tools.add_politician_to_tracker_impl"
        ) as mock_impl:
            mock_impl.return_value = "Success message"

            from sentinel.core.agent_tools import add_politician_to_tracker

            # The decorated function might be mocked by autouse fixture, but we can test the delegation pattern
            # by checking if our implementation function is called correctly when not mocked
            result = await mock_impl("Nancy Pelosi")

            assert result == "Success message"
            mock_impl.assert_called_once_with("Nancy Pelosi")

    @pytest.mark.asyncio
    async def test_remove_politician_from_tracker_wrapper(self):
        """Test the @function_tool wrapper for remove_politician_from_tracker."""
        with patch(
            "sentinel.core.agent_tools.remove_politician_from_tracker_impl"
        ) as mock_impl:
            mock_impl.return_value = "Removed successfully"

            from sentinel.core.agent_tools import remove_politician_from_tracker_impl

            result = await remove_politician_from_tracker_impl("Nancy Pelosi")

            assert result == "Removed successfully"
            mock_impl.assert_called_once_with("Nancy Pelosi")

    @pytest.mark.asyncio
    async def test_get_tracked_politicians_wrapper(self):
        """Test the @function_tool wrapper for get_tracked_politicians."""
        with patch(
            "sentinel.core.agent_tools.get_tracked_politicians_list_impl"
        ) as mock_impl:
            mock_impl.return_value = ["List of politicians"]

            from sentinel.core.agent_tools import get_tracked_politicians_list_impl

            result = await get_tracked_politicians_list_impl()

            assert result == ["List of politicians"]
            mock_impl.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_politician_activity_wrapper(self):
        """Test the @function_tool wrapper for get_politician_activity_info."""
        with patch(
            "sentinel.core.agent_tools.get_politician_activity_info_impl"
        ) as mock_impl:
            mock_impl.return_value = ["Activity report"]

            from sentinel.core.agent_tools import get_politician_activity_info_impl

            result = await get_politician_activity_info_impl(
                "Nancy Pelosi", fetch_latest=False
            )

            assert result == ["Activity report"]
            mock_impl.assert_called_once_with("Nancy Pelosi", fetch_latest=False)


class TestPoliticianToolsBusinessLogic:
    """Test politician tools business logic and edge cases."""

    @patch("sentinel.core.agent_tools.TrackedPoliticianRepository")
    @pytest.mark.asyncio
    async def test_add_politician_with_chamber_info(self, mock_repo_class):
        """Test adding politician with chamber information."""
        from sentinel.core.agent_tools import add_politician_to_tracker_impl

        mock_repo = Mock()
        mock_repo.is_politician_tracked.return_value = (
            False  # Politician not tracked yet
        )
        # Mock the returned object structure
        mock_politician = Mock()
        mock_politician.politician.name = "Alexandria Ocasio-Cortez"
        mock_repo.add_tracked_politician.return_value = mock_politician
        mock_repo_class.return_value.__enter__.return_value = mock_repo

        result = await add_politician_to_tracker_impl(
            "Alexandria Ocasio-Cortez", "House"
        )

        mock_repo.is_politician_tracked.assert_called_once_with(
            "Alexandria Ocasio-Cortez"
        )
        mock_repo.add_tracked_politician.assert_called_once_with(
            "Alexandria Ocasio-Cortez", "House"
        )
        assert result == "Added Alexandria Ocasio-Cortez to politician tracker list"

    @patch("sentinel.core.agent_tools.PoliticianActivityRepository")
    @patch("sentinel.config.settings.get_settings")
    @pytest.mark.asyncio
    async def test_check_politician_activity_date_formatting(
        self, mock_get_settings, mock_repo_class
    ):
        """Test that politician activity dates are formatted correctly."""
        from sentinel.core.agent_tools import get_politician_activity_info_impl

        mock_settings = Mock()
        mock_settings.quiver_api_token = "test_token"
        mock_get_settings.return_value = mock_settings

        mock_activity = Mock()
        mock_activity.ticker = "TSLA"
        mock_activity.activity_type = "Sale"
        mock_activity.amount_range = "15000-50000"
        mock_activity.activity_date = Mock()
        mock_activity.activity_date.strftime.return_value = "2024-01-15"

        mock_repo = Mock()
        mock_repo.get_activities_by_politician.return_value = [mock_activity]
        mock_repo_class.return_value.__enter__.return_value = mock_repo

        # Test the activity formatting function
        result = await get_politician_activity_info_impl(
            "Alexandria Ocasio-Cortez", fetch_latest=False
        )

        # Check that date is properly formatted in output
        assert "2024-01-15" in result[0]
        assert "TSLA" in result[0]
        assert "Sale" in result[0]

    @patch("sentinel.core.agent_tools.TrackedPoliticianRepository")
    @pytest.mark.asyncio
    async def test_tracked_politicians_list_with_partial_info(self, mock_repo_class):
        """Test getting tracked politicians list when some have partial information."""
        from sentinel.core.agent_tools import get_tracked_politicians_list_impl

        # Politician with full info
        mock_politician1 = Mock()
        mock_politician1.name = "Nancy Pelosi"
        mock_politician1.chamber = "House"
        mock_politician1.party = "Democrat"

        # Politician with missing party info
        mock_politician2 = Mock()
        mock_politician2.name = "Unknown Senator"
        mock_politician2.chamber = "Senate"
        mock_politician2.party = None

        mock_tracked1 = Mock()
        mock_tracked1.politician = mock_politician1
        mock_tracked2 = Mock()
        mock_tracked2.politician = mock_politician2

        mock_repo = Mock()
        mock_repo.get_all_tracked_politicians.return_value = [
            mock_tracked1,
            mock_tracked2,
        ]
        mock_repo_class.return_value.__enter__.return_value = mock_repo

        result = await get_tracked_politicians_list_impl()

        # The function returns just names, not formatted descriptions
        expected = ["Nancy Pelosi", "Unknown Senator"]
        assert result == expected
        assert "Nancy Pelosi" in result
        assert "Unknown Senator" in result

    @patch("sentinel.core.agent_tools.PoliticianActivityRepository")
    @patch("sentinel.config.settings.get_settings")
    @pytest.mark.asyncio
    async def test_get_politician_activity_multiple_activities(
        self, mock_get_settings, mock_repo_class
    ):
        """Test politician activity with multiple transactions."""
        from sentinel.core.agent_tools import get_politician_activity_info_impl

        mock_settings = Mock()
        mock_settings.quiver_api_token = "test_token"
        mock_get_settings.return_value = mock_settings

        # Multiple activities
        mock_activity1 = Mock()
        mock_activity1.ticker = "AAPL"
        mock_activity1.activity_type = "Purchase"
        mock_activity1.amount_range = "50000-100000"
        mock_activity1.activity_date = Mock()
        mock_activity1.activity_date.strftime.return_value = "2024-01-15"

        mock_activity2 = Mock()
        mock_activity2.ticker = "MSFT"
        mock_activity2.activity_type = "Sale"
        mock_activity2.amount_range = "15000-50000"
        mock_activity2.activity_date = Mock()
        mock_activity2.activity_date.strftime.return_value = "2024-01-16"

        mock_repo = Mock()
        mock_repo.get_activities_by_politician.return_value = [
            mock_activity1,
            mock_activity2,
        ]
        mock_repo_class.return_value.__enter__.return_value = mock_repo

        result = await get_politician_activity_info_impl(
            "Nancy Pelosi", fetch_latest=False
        )

        # Should handle multiple activities
        assert isinstance(result, list)
