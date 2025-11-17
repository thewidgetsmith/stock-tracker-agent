"""Tests for core stock checker functionality."""

import sys
from unittest.mock import Mock, patch

import pytest

sys.path.append("src")


class TestStockChecker:
    """Test stock price checking operations."""

    @patch("sentinel.core.stock_query.yf")
    def test_get_stock_price_success(self, mock_yf):
        """Test successful stock price retrieval."""
        from sentinel.core.stock_query import get_stock_price

        # Setup mock yfinance ticker with proper nested structure
        mock_ticker = Mock()

        # Mock history data - need to return a pandas-like structure
        mock_history_data = Mock()
        mock_history_data.__getitem__ = Mock(
            return_value=Mock(
                dropna=Mock(
                    return_value=Mock(
                        iloc=Mock(
                            __getitem__=Mock(
                                side_effect=lambda x: 148.0 if x == -2 else 150.0
                            )
                        )
                    )
                )
            )
        )
        mock_ticker.history.return_value = mock_history_data

        # Mock fast_info
        mock_ticker.fast_info.last_price = 150.0

        # Mock info
        mock_ticker.info = {"symbol": "AAPL"}

        mock_yf.Ticker.return_value = mock_ticker

        result = get_stock_price("AAPL")

        # Verify the result
        assert result.current_price == 150.0
        assert result.previous_close == 148.0

        # Verify yfinance was called correctly
        mock_yf.Ticker.assert_called_once_with("AAPL")
        assert mock_ticker.history.call_count == 2  # Called for 1d and 5d data
        mock_ticker.history.assert_any_call(period="1d", interval="1m")
        mock_ticker.history.assert_any_call(period="5d")

    @patch("sentinel.core.stock_query.yf")
    def test_get_stock_price_ticker_error(self, mock_yf):
        """Test error handling when yfinance ticker creation fails."""
        from sentinel.core.stock_query import get_stock_price

        mock_yf.Ticker.side_effect = Exception("Network error")

        with pytest.raises(Exception, match="Network error"):
            get_stock_price("INVALID")

    @patch("sentinel.core.stock_query.yf")
    def test_get_stock_price_history_error(self, mock_yf):
        """Test error handling when history data is unavailable."""
        from sentinel.core.stock_query import get_stock_price

        mock_ticker = Mock()
        mock_ticker.history.side_effect = Exception("History unavailable")
        mock_yf.Ticker.return_value = mock_ticker

        with pytest.raises(Exception, match="History unavailable"):
            get_stock_price("AAPL")

    @patch("sentinel.core.stock_query.yf")
    def test_get_stock_price_missing_data(self, mock_yf):
        """Test handling when some data is missing."""
        from sentinel.core.stock_query import get_stock_price

        mock_ticker = Mock()

        # Mock empty history
        mock_history_data = Mock()
        mock_history_data.__getitem__ = Mock(
            return_value=Mock(
                dropna=Mock(
                    return_value=Mock(
                        iloc=Mock(__getitem__=Mock(side_effect=IndexError("No data")))
                    )
                )
            )
        )
        mock_ticker.history.return_value = mock_history_data

        mock_yf.Ticker.return_value = mock_ticker

        with pytest.raises(IndexError, match="No data"):
            get_stock_price("AAPL")

    def test_stock_price_response_model(self):
        """Test StockPriceResponse model creation."""
        from sentinel.core.stock_query import StockPriceResponse

        response = StockPriceResponse(current_price=150.0, previous_close=148.0)

        assert response.current_price == 150.0
        assert response.previous_close == 148.0

    def test_stock_price_response_validation(self):
        """Test StockPriceResponse validation."""
        from pydantic import ValidationError

        from sentinel.core.stock_query import StockPriceResponse

        # Test invalid data types
        with pytest.raises(ValidationError):
            StockPriceResponse(
                current_price="invalid", previous_close=148.0  # Should be float
            )

    @patch("sentinel.core.stock_query.yf")
    def test_get_stock_price_empty_data_fallback(self, mock_yf):
        """Test fallback when 1-day data is empty."""
        from sentinel.core.stock_query import get_stock_price

        mock_ticker = Mock()

        # Mock empty 1-day data (triggers fallback)
        mock_empty_data = Mock()
        mock_empty_data.empty = True

        # Mock 5-day data for previous close
        mock_5d_data = Mock()
        mock_5d_data.__getitem__ = Mock(
            return_value=Mock(
                dropna=Mock(
                    return_value=Mock(iloc=Mock(__getitem__=Mock(return_value=148.0)))
                )
            )
        )

        # Configure history to return empty data for 1d, regular data for 5d
        def history_side_effect(period, interval=None):
            if period == "1d":
                return mock_empty_data
            elif period == "5d":
                return mock_5d_data

        mock_ticker.history.side_effect = history_side_effect
        mock_ticker.fast_info.last_price = 150.0  # Fallback price

        mock_yf.Ticker.return_value = mock_ticker

        result = get_stock_price("AAPL")

        assert result.current_price == 150.0  # From fast_info fallback
        assert result.previous_close == 148.0

        # Verify both calls were made
        assert mock_ticker.history.call_count == 2

    @patch("sentinel.core.stock_query.yf")
    def test_multiple_stock_calls(self, mock_yf):
        """Test multiple sequential stock price calls."""
        from sentinel.core.stock_query import get_stock_price

        # Setup different mock responses for different symbols
        def mock_ticker_factory(symbol):
            mock_ticker = Mock()

            prices = {"AAPL": (150.0, 148.0), "GOOGL": (2800.0, 2750.0)}
            current, previous = prices.get(symbol, (100.0, 98.0))

            mock_history_data = Mock()
            mock_history_data.__getitem__ = Mock(
                return_value=Mock(
                    dropna=Mock(
                        return_value=Mock(
                            iloc=Mock(
                                __getitem__=Mock(
                                    side_effect=lambda x: (
                                        previous if x == -2 else current
                                    )
                                )
                            )
                        )
                    )
                )
            )
            mock_ticker.history.return_value = mock_history_data
            mock_ticker.fast_info.last_price = current
            mock_ticker.info = {"symbol": symbol}

            return mock_ticker

        mock_yf.Ticker.side_effect = mock_ticker_factory

        # Test multiple calls
        aapl_result = get_stock_price("AAPL")
        googl_result = get_stock_price("GOOGL")

        assert aapl_result.current_price == 150.0
        assert aapl_result.previous_close == 148.0

        assert googl_result.current_price == 2800.0
        assert googl_result.previous_close == 2750.0

        assert mock_yf.Ticker.call_count == 2
