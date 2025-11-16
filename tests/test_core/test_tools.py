"""Tests for core tools functionality."""

import json

# Import modules to test
import sys
from unittest.mock import Mock, mock_open, patch

import pytest

sys.path.append("src")
from sentinel.core.tools import (
    add_stock_to_tracker,
    get_stock_price_info,
    get_tracked_stocks_list,
    remove_stock_from_tracker,
)


class TestGetStockPriceInfo:
    """Test the get_stock_price_info function."""

    @patch("sentinel.core.tools.get_stock_price")
    def test_successful_stock_price_retrieval(self, mock_get_price):
        """Test successful stock price retrieval."""
        # Setup mock
        mock_price_data = Mock()
        mock_price_data.current_price = 150.0
        mock_price_data.previous_close = 148.0
        mock_price_data.symbol = "AAPL"
        mock_get_price.return_value = mock_price_data

        result = get_stock_price_info("AAPL")

        assert "AAPL" in result
        assert "150.0" in result
        assert "148.0" in result
        mock_get_price.assert_called_once_with("AAPL")

    @patch("sentinel.core.tools.get_stock_price")
    def test_stock_price_error_handling(self, mock_get_price):
        """Test error handling when stock price retrieval fails."""
        mock_get_price.side_effect = Exception("API Error")

        result = get_stock_price_info("INVALID")

        assert "Error" in result
        assert "INVALID" in result


class TestTrackerOperations:
    """Test tracking list operations."""

    def test_add_stock_to_tracker_new_file(self, temp_resources_dir):
        """Test adding stock to tracker when file is empty."""
        tracker_file = temp_resources_dir / "tracker_list.json"

        with patch("sentinel.core.tools.Path") as mock_path:
            mock_path.return_value = tracker_file

            result = add_stock_to_tracker("AAPL")

            assert "added" in result.lower()
            assert "AAPL" in result

            # Verify file contents
            with open(tracker_file, "r") as f:
                data = json.load(f)
            assert "AAPL" in data

    def test_add_stock_already_exists(self, temp_resources_dir):
        """Test adding stock that already exists in tracker."""
        tracker_file = temp_resources_dir / "tracker_list.json"

        # Pre-populate with AAPL
        with open(tracker_file, "w") as f:
            json.dump(["AAPL"], f)

        with patch("sentinel.core.tools.Path") as mock_path:
            mock_path.return_value = tracker_file

            result = add_stock_to_tracker("AAPL")

            assert "already" in result.lower()
            assert "AAPL" in result

    def test_remove_stock_from_tracker_success(self, temp_resources_dir):
        """Test successfully removing stock from tracker."""
        tracker_file = temp_resources_dir / "tracker_list.json"

        # Pre-populate with stocks
        with open(tracker_file, "w") as f:
            json.dump(["AAPL", "GOOGL"], f)

        with patch("sentinel.core.tools.Path") as mock_path:
            mock_path.return_value = tracker_file

            result = remove_stock_from_tracker("AAPL")

            assert "removed" in result.lower()
            assert "AAPL" in result

            # Verify file contents
            with open(tracker_file, "r") as f:
                data = json.load(f)
            assert "AAPL" not in data
            assert "GOOGL" in data

    def test_remove_stock_not_found(self, temp_resources_dir):
        """Test removing stock that doesn't exist in tracker."""
        tracker_file = temp_resources_dir / "tracker_list.json"

        with patch("sentinel.core.tools.Path") as mock_path:
            mock_path.return_value = tracker_file

            result = remove_stock_from_tracker("TSLA")

            assert "not found" in result.lower() or "not in" in result.lower()
            assert "TSLA" in result

    def test_get_tracked_stocks_list_empty(self, temp_resources_dir):
        """Test getting empty tracker list."""
        tracker_file = temp_resources_dir / "tracker_list.json"

        with patch("sentinel.core.tools.Path") as mock_path:
            mock_path.return_value = tracker_file

            result = get_tracked_stocks_list()

            assert "empty" in result.lower() or "no stocks" in result.lower()

    def test_get_tracked_stocks_list_with_stocks(self, temp_resources_dir):
        """Test getting tracker list with stocks."""
        tracker_file = temp_resources_dir / "tracker_list.json"

        # Pre-populate with stocks
        stocks = ["AAPL", "GOOGL", "MSFT"]
        with open(tracker_file, "w") as f:
            json.dump(stocks, f)

        with patch("sentinel.core.tools.Path") as mock_path:
            mock_path.return_value = tracker_file

            result = get_tracked_stocks_list()

            for stock in stocks:
                assert stock in result
            assert "tracking" in result.lower()

    def test_tracker_operations_file_creation(self, tmp_path):
        """Test that tracker operations create necessary files."""
        tracker_file = tmp_path / "new_tracker.json"

        with patch("sentinel.core.tools.Path") as mock_path:
            mock_path.return_value = tracker_file

            # File doesn't exist yet
            assert not tracker_file.exists()

            # Adding stock should create the file
            add_stock_to_tracker("AAPL")

            assert tracker_file.exists()

            # Verify contents
            with open(tracker_file, "r") as f:
                data = json.load(f)
            assert data == ["AAPL"]


@pytest.mark.parametrize(
    "symbol,expected_in_result",
    [
        ("AAPL", ["AAPL", "Apple"]),
        ("GOOGL", ["GOOGL", "Google"]),
        ("MSFT", ["MSFT", "Microsoft"]),
    ],
)
def test_stock_symbols_handling(symbol, expected_in_result):
    """Test handling of different stock symbols."""
    with patch("sentinel.core.tools.get_stock_price") as mock_get_price:
        mock_price_data = Mock()
        mock_price_data.current_price = 100.0
        mock_price_data.previous_close = 98.0
        mock_price_data.symbol = symbol
        mock_get_price.return_value = mock_price_data

        result = get_stock_price_info(symbol)

        # Check that at least one expected string is in the result
        assert any(expected in result for expected in expected_in_result)
