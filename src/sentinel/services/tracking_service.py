"""Tracking service for stock monitoring and portfolio management."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Set

from ..config.logging import get_logger
from ..ormdb.database import get_session
from ..ormdb.repositories import TrackedStockRepository
from .stock_service import MovementThreshold, StockAnalysis, StockService

logger = get_logger(__name__)


@dataclass
class TrackingPortfolio:
    """Portfolio of tracked stocks with metadata."""

    tracked_stocks: List[str]
    total_count: int
    active_count: int
    last_updated: datetime


@dataclass
class StockTrackingResult:
    """Result of stock tracking operation."""

    symbol: str
    analysis: Optional[StockAnalysis]
    alert_triggered: bool
    error: Optional[str]
    processing_time_ms: float


class TrackingService:
    """Service for stock tracking and monitoring operations."""

    def __init__(self, stock_service: Optional[StockService] = None):
        self.stock_service = stock_service or StockService()
        self.logger = logger.bind(service="tracking_service")

    async def add_stock_to_tracking(self, symbol: str) -> dict:
        """
        Add a stock to the tracking portfolio.

        Args:
            symbol: Stock symbol to add

        Returns:
            Result dictionary with operation status
        """
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Symbol must be a non-empty string")

        symbol = symbol.upper().strip()

        self.logger.info("Adding stock to tracking", symbol=symbol)

        # Validate stock exists
        is_valid = await self.stock_service.validate_stock_symbol(symbol)
        if not is_valid:
            error_msg = f"Stock symbol '{symbol}' is not valid or not tradeable"
            self.logger.warning("Invalid stock symbol", symbol=symbol)
            return {
                "success": False,
                "symbol": symbol,
                "message": error_msg,
                "reason": "invalid_symbol",
            }

        # Add to tracking using repository
        session_gen = get_session()
        session = next(session_gen)

        try:
            with TrackedStockRepository(session) as repo:
                existing_stock = repo.get_stock_by_symbol(symbol)

                if existing_stock and existing_stock.is_active:
                    self.logger.info("Stock already being tracked", symbol=symbol)
                    return {
                        "success": True,
                        "symbol": symbol,
                        "message": f"{symbol} is already being tracked",
                        "reason": "already_tracked",
                    }

                # Add or reactivate stock
                if existing_stock and not existing_stock.is_active:
                    existing_stock.is_active = True
                    session.commit()
                    action = "reactivated"
                else:
                    repo.add_stock(symbol)
                    action = "added"

                self.logger.info("Stock tracking updated", symbol=symbol, action=action)

                return {
                    "success": True,
                    "symbol": symbol,
                    "message": f"Successfully {action} {symbol} to tracking",
                    "action": action,
                }

        except Exception as e:
            self.logger.error(
                "Failed to add stock to tracking",
                symbol=symbol,
                error=str(e),
                exc_info=True,
            )
            return {
                "success": False,
                "symbol": symbol,
                "message": f"Failed to add {symbol} to tracking: {str(e)}",
                "reason": "database_error",
            }
        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass

    async def remove_stock_from_tracking(self, symbol: str) -> dict:
        """
        Remove a stock from tracking portfolio.

        Args:
            symbol: Stock symbol to remove

        Returns:
            Result dictionary with operation status
        """
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Symbol must be a non-empty string")

        symbol = symbol.upper().strip()

        self.logger.info("Removing stock from tracking", symbol=symbol)

        session_gen = get_session()
        session = next(session_gen)

        try:
            with TrackedStockRepository(session) as repo:
                success = repo.remove_stock(symbol)

                if success:
                    self.logger.info("Stock removed from tracking", symbol=symbol)
                    return {
                        "success": True,
                        "symbol": symbol,
                        "message": f"Successfully removed {symbol} from tracking",
                    }
                else:
                    self.logger.warning("Stock not found in tracking", symbol=symbol)
                    return {
                        "success": False,
                        "symbol": symbol,
                        "message": f"{symbol} is not currently being tracked",
                        "reason": "not_tracked",
                    }

        except Exception as e:
            self.logger.error(
                "Failed to remove stock from tracking",
                symbol=symbol,
                error=str(e),
                exc_info=True,
            )
            return {
                "success": False,
                "symbol": symbol,
                "message": f"Failed to remove {symbol} from tracking: {str(e)}",
                "reason": "database_error",
            }
        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass

    async def get_tracking_portfolio(self) -> TrackingPortfolio:
        """
        Get the current tracking portfolio.

        Returns:
            TrackingPortfolio with all tracked stocks
        """
        self.logger.info("Retrieving tracking portfolio")

        session_gen = get_session()
        session = next(session_gen)

        try:
            with TrackedStockRepository(session) as repo:
                active_stocks = repo.get_all_active_stocks()
                symbols = [stock.symbol for stock in active_stocks]

                portfolio = TrackingPortfolio(
                    tracked_stocks=symbols,
                    total_count=len(symbols),
                    active_count=len(symbols),
                    last_updated=datetime.utcnow(),
                )

                self.logger.info(
                    "Tracking portfolio retrieved",
                    stock_count=len(symbols),
                    symbols=symbols,
                )

                return portfolio

        except Exception as e:
            self.logger.error(
                "Failed to retrieve tracking portfolio", error=str(e), exc_info=True
            )
            # Return empty portfolio on error
            return TrackingPortfolio(
                tracked_stocks=[],
                total_count=0,
                active_count=0,
                last_updated=datetime.utcnow(),
            )
        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass

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

        portfolio = await self.get_tracking_portfolio()

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
            analysis = await self.stock_service.analyze_stock_movement(
                symbol, threshold
            )

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
        portfolio = await self.get_tracking_portfolio()

        # Get performance data for all stocks
        stock_performances = []
        for symbol in portfolio.tracked_stocks[:10]:  # Limit to prevent API overload
            try:
                performance = await self.stock_service.get_stock_performance_summary(
                    symbol
                )
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
