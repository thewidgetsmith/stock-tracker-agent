"""Portfolio management for stock tracking."""

from datetime import datetime

from ...config.logging import get_logger
from ...ormdb.database import get_session
from ...ormdb.repositories import TrackedStockRepository
from .models import TrackingPortfolio

logger = get_logger(__name__)


class PortfolioManager:
    """Manages the stock tracking portfolio."""

    def __init__(self):
        self.logger = logger.bind(component="portfolio_manager")

    async def add_stock(self, symbol: str, validate_func) -> dict:
        """
        Add a stock to the tracking portfolio.

        Args:
            symbol: Stock symbol to add
            validate_func: Async function to validate stock symbol

        Returns:
            Result dictionary with operation status
        """
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Symbol must be a non-empty string")

        symbol = symbol.upper().strip()

        self.logger.info("Adding stock to tracking", symbol=symbol)

        # Validate stock exists
        is_valid = await validate_func(symbol)
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

                if existing_stock and existing_stock.is_active:  # type: ignore
                    self.logger.info("Stock already being tracked", symbol=symbol)
                    return {
                        "success": True,
                        "symbol": symbol,
                        "message": f"{symbol} is already being tracked",
                        "reason": "already_tracked",
                    }

                # Add or reactivate stock
                if existing_stock and not existing_stock.is_active:  # type: ignore
                    existing_stock.is_active = True  # type: ignore
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

    async def remove_stock(self, symbol: str) -> dict:
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

    async def get_portfolio(self) -> TrackingPortfolio:
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
                symbols = [stock.symbol for stock in active_stocks]  # type: ignore

                portfolio = TrackingPortfolio(
                    tracked_stocks=symbols,  # type: ignore
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
