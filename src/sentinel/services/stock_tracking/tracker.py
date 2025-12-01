"""Bulk stock tracking operations."""

from datetime import datetime
from typing import List

from ...config.logging import get_logger
from .models import MovementThreshold, StockTrackingResult

logger = get_logger(__name__)


class StockTracker:
    """Handles bulk stock tracking operations."""

    def __init__(self, stock_ops, portfolio_mgr):
        self.stock_ops = stock_ops
        self.portfolio_mgr = portfolio_mgr
        self.logger = logger.bind(component="stock_tracker")

    async def track_all_stocks(
        self, movement_threshold: MovementThreshold = MovementThreshold.MODERATE
    ) -> List[StockTrackingResult]:
        """
        Track all stocks in portfolio for significant movements.

        Args:
            movement_threshold: Threshold for significant movement detection

        Returns:
            List of tracking results for each stock
        """
        self.logger.info("Starting portfolio-wide stock tracking")
        start_time = datetime.utcnow()

        portfolio = await self.portfolio_mgr.get_portfolio()

        if not portfolio.tracked_stocks:
            self.logger.info("No stocks in tracking portfolio")
            return []

        results = []

        for symbol in portfolio.tracked_stocks:
            stock_start = datetime.utcnow()
            result = await self._track_single_stock(symbol, movement_threshold)
            result.processing_time_ms = (
                datetime.utcnow() - stock_start
            ).total_seconds() * 1000
            results.append(result)

        total_time = (datetime.utcnow() - start_time).total_seconds()
        significant_movements = sum(1 for r in results if r.alert_triggered)

        self.logger.info(
            "Portfolio tracking completed",
            total_stocks=len(portfolio.tracked_stocks),
            significant_movements=significant_movements,
            processing_time_seconds=total_time,
        )

        return results

    async def _track_single_stock(
        self, symbol: str, threshold: MovementThreshold
    ) -> StockTrackingResult:
        """
        Track a single stock for significant movements.

        Args:
            symbol: Stock symbol to track
            threshold: Movement threshold

        Returns:
            StockTrackingResult for the stock
        """
        try:
            analysis = await self.stock_ops.analyze_stock_movement(symbol, threshold)

            self.logger.info(
                "Stock tracking analysis completed",
                symbol=symbol,
                price_change_percent=analysis.price_change_percent,
                is_significant=analysis.is_significant_movement,
            )

            return StockTrackingResult(
                symbol=symbol,
                analysis=analysis,
                alert_triggered=analysis.is_significant_movement,
                error=None,
                processing_time_ms=0,  # Will be set by caller
            )

        except Exception as e:
            self.logger.error(
                "Failed to track stock", symbol=symbol, error=str(e), exc_info=True
            )

            return StockTrackingResult(
                symbol=symbol,
                analysis=None,
                alert_triggered=False,
                error=str(e),
                processing_time_ms=0,  # Will be set by caller
            )

    async def get_portfolio_summary(self) -> dict:
        """
        Get comprehensive portfolio tracking summary.

        Returns:
            Dictionary with portfolio metrics and status
        """
        portfolio = await self.portfolio_mgr.get_portfolio()

        # Get performance data for all stocks
        stock_performances = []
        for symbol in portfolio.tracked_stocks[:10]:  # Limit to prevent API overload
            try:
                performance = await self.stock_ops.get_stock_performance_summary(symbol)
                stock_performances.append(performance)
            except Exception as e:
                self.logger.warning(
                    "Failed to get performance for stock", symbol=symbol, error=str(e)
                )

        # Calculate portfolio metrics
        portfolio_metrics = self._calculate_portfolio_metrics(stock_performances)

        return {
            "portfolio": {
                "total_stocks": portfolio.total_count,
                "active_stocks": portfolio.active_count,
                "tracked_symbols": portfolio.tracked_stocks,
                "last_updated": portfolio.last_updated.isoformat(),
            },
            "performance": portfolio_metrics,
            "stock_details": stock_performances,
        }

    def _calculate_portfolio_metrics(self, performances: List[dict]) -> dict:
        """
        Calculate aggregate portfolio metrics.

        Args:
            performances: List of stock performance dictionaries

        Returns:
            Portfolio metrics dictionary
        """
        if not performances:
            return {
                "average_change_percent": 0.0,
                "positive_movers": 0,
                "negative_movers": 0,
                "stable_stocks": 0,
                "significant_movements": 0,
            }

        changes = [p["price_change_percent"] for p in performances]
        avg_change = sum(changes) / len(changes)

        positive_movers = sum(1 for change in changes if change > 0)
        negative_movers = sum(1 for change in changes if change < 0)
        stable_stocks = len(changes) - positive_movers - negative_movers

        significant_movements = sum(
            1 for p in performances if p.get("is_significant", False)
        )

        return {
            "average_change_percent": round(avg_change, 4),
            "positive_movers": positive_movers,
            "negative_movers": negative_movers,
            "stable_stocks": stable_stocks,
            "significant_movements": significant_movements,
            "total_analyzed": len(performances),
        }
