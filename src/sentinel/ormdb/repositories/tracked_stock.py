"""Repository for tracked stock operations."""

from typing import List, Optional

from sqlalchemy.orm import Session

from ..models import TrackedStock
from .base import BaseRepository


class TrackedStockRepository(BaseRepository):
    """Repository for tracked stock operations."""

    def add_stock(self, symbol: str) -> TrackedStock:
        """Add a stock to the tracking list."""
        # Check if stock already exists
        existing_stock = self.get_stock_by_symbol(symbol)
        if existing_stock:
            if not existing_stock.is_active:
                # Reactivate if it was deactivated
                existing_stock.is_active = True
                self.session.commit()
            return existing_stock

        stock = TrackedStock(symbol=symbol.upper())
        self.session.add(stock)
        self.session.commit()
        self.session.refresh(stock)

        return stock

    def remove_stock(self, symbol: str) -> bool:
        """Remove a stock from tracking (soft delete)."""
        stock = self.get_stock_by_symbol(symbol)
        if stock and stock.is_active:
            stock.is_active = False
            self.session.commit()
            return True
        return False

    def get_stock_by_symbol(self, symbol: str) -> Optional[TrackedStock]:
        """Get a tracked stock by symbol."""
        return (
            self.session.query(TrackedStock)
            .filter(TrackedStock.symbol == symbol.upper())
            .first()
        )

    def get_all_active_stocks(self) -> List[TrackedStock]:
        """Get all actively tracked stocks."""
        return (
            self.session.query(TrackedStock)
            .filter(TrackedStock.is_active == True)
            .order_by(TrackedStock.symbol)
            .all()
        )

    def get_stock_symbols(self) -> List[str]:
        """Get list of all tracked stock symbols."""
        stocks = self.get_all_active_stocks()
        return [stock.symbol for stock in stocks]
