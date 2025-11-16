"""Stock service for stock-related business operations."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional

from ..config.logging import get_logger
from ..core.stock_checker import StockPriceResponse, get_stock_price
from ..db.database import get_session
from ..db.repositories import TrackedStockRepository

logger = get_logger(__name__)


@dataclass
class StockAnalysis:
    """Stock analysis data container."""

    symbol: str
    current_price: float
    previous_close: float
    price_change: float
    price_change_percent: float
    volume: Optional[int]
    market_cap: Optional[float]
    analysis_timestamp: datetime
    is_significant_movement: bool


class MovementThreshold(Enum):
    """Price movement significance thresholds."""

    MINOR = 0.005  # 0.5%
    MODERATE = 0.01  # 1%
    SIGNIFICANT = 0.05  # 5%
    MAJOR = 0.10  # 10%


class StockService:
    """Service for stock-related business operations."""

    def __init__(self):
        self.logger = logger.bind(service="stock_service")

    async def get_stock_price(self, symbol: str) -> StockPriceResponse:
        """
        Get current stock price information.

        Args:
            symbol: Stock symbol to fetch price for

        Returns:
            StockPriceResponse with current price data

        Raises:
            ValueError: If symbol is invalid
            Exception: If stock data cannot be fetched
        """
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Symbol must be a non-empty string")

        symbol = symbol.upper().strip()

        self.logger.info("Fetching stock price", symbol=symbol)

        try:
            stock_data = get_stock_price(symbol)

            self.logger.info(
                "Stock price fetched successfully",
                symbol=symbol,
                current_price=stock_data.current_price,
                previous_close=stock_data.previous_close,
            )

            return stock_data

        except Exception as e:
            self.logger.error(
                "Failed to fetch stock price",
                symbol=symbol,
                error=str(e),
                exc_info=True,
            )
            raise

    async def analyze_stock_movement(
        self, symbol: str, threshold: MovementThreshold = MovementThreshold.MODERATE
    ) -> StockAnalysis:
        """
        Analyze stock price movement and determine significance.

        Args:
            symbol: Stock symbol to analyze
            threshold: Significance threshold for movement detection

        Returns:
            StockAnalysis with movement analysis
        """
        stock_data = await self.get_stock_price(symbol)

        # Calculate price changes
        price_change = stock_data.current_price - stock_data.previous_close
        price_change_percent = (
            stock_data.current_price / stock_data.previous_close
        ) - 1

        # Determine if movement is significant
        is_significant = abs(price_change_percent) >= threshold.value

        analysis = StockAnalysis(
            symbol=symbol,
            current_price=stock_data.current_price,
            previous_close=stock_data.previous_close,
            price_change=price_change,
            price_change_percent=price_change_percent,
            volume=stock_data.volume,
            market_cap=stock_data.market_cap,
            analysis_timestamp=datetime.utcnow(),
            is_significant_movement=is_significant,
        )

        self.logger.info(
            "Stock movement analyzed",
            symbol=symbol,
            price_change_percent=price_change_percent,
            is_significant=is_significant,
            threshold=threshold.value,
        )

        return analysis

    async def get_multiple_stock_prices(
        self, symbols: List[str]
    ) -> List[StockPriceResponse]:
        """
        Get stock prices for multiple symbols.

        Args:
            symbols: List of stock symbols

        Returns:
            List of StockPriceResponse objects
        """
        if not symbols:
            return []

        results = []
        failed_symbols = []

        self.logger.info("Fetching multiple stock prices", symbols=symbols)

        for symbol in symbols:
            try:
                stock_data = await self.get_stock_price(symbol)
                results.append(stock_data)
            except Exception as e:
                failed_symbols.append(symbol)
                self.logger.warning(
                    "Failed to fetch stock price in batch", symbol=symbol, error=str(e)
                )

        if failed_symbols:
            self.logger.warning(
                "Some stock prices could not be fetched",
                failed_symbols=failed_symbols,
                successful_count=len(results),
                total_count=len(symbols),
            )

        return results

    async def validate_stock_symbol(self, symbol: str) -> bool:
        """
        Validate if a stock symbol exists and is tradeable.

        Args:
            symbol: Stock symbol to validate

        Returns:
            True if symbol is valid and tradeable
        """
        try:
            await self.get_stock_price(symbol)
            return True
        except Exception as e:
            self.logger.info(
                "Stock symbol validation failed", symbol=symbol, error=str(e)
            )
            return False

    async def get_stock_performance_summary(self, symbol: str) -> dict:
        """
        Get comprehensive stock performance summary.

        Args:
            symbol: Stock symbol to analyze

        Returns:
            Dictionary with performance metrics
        """
        analysis = await self.analyze_stock_movement(symbol)

        return {
            "symbol": analysis.symbol,
            "current_price": analysis.current_price,
            "previous_close": analysis.previous_close,
            "price_change": analysis.price_change,
            "price_change_percent": analysis.price_change_percent,
            "volume": analysis.volume,
            "market_cap": analysis.market_cap,
            "movement_classification": self._classify_movement(
                analysis.price_change_percent
            ),
            "analysis_timestamp": analysis.analysis_timestamp.isoformat(),
            "is_significant": analysis.is_significant_movement,
        }

    def _classify_movement(self, change_percent: float) -> str:
        """
        Classify price movement based on percentage change.

        Args:
            change_percent: Percentage change in price

        Returns:
            Movement classification string
        """
        abs_change = abs(change_percent)

        if abs_change >= MovementThreshold.MAJOR.value:
            direction = "surge" if change_percent > 0 else "crash"
            return f"major_{direction}"
        elif abs_change >= MovementThreshold.SIGNIFICANT.value:
            direction = "rally" if change_percent > 0 else "drop"
            return f"significant_{direction}"
        elif abs_change >= MovementThreshold.MODERATE.value:
            direction = "rise" if change_percent > 0 else "decline"
            return f"moderate_{direction}"
        elif abs_change >= MovementThreshold.MINOR.value:
            direction = "uptick" if change_percent > 0 else "dip"
            return f"minor_{direction}"
        else:
            return "stable"
