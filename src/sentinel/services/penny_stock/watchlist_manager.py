"""Watch list management for penny stocks."""

from datetime import datetime
from typing import List

from ...config.logging import get_logger
from ...ormdb.database import get_session
from ...ormdb.penny_stock_models import PennyStockWatch
from .models import PennyStockCandidate

logger = get_logger(__name__)


class WatchlistManager:
    """Manages penny stock watch list."""

    def __init__(self):
        self.logger = logger.bind(component="watchlist_manager")

    async def get_existing_symbols(self) -> List[str]:
        """Get symbols already in penny stock watch table."""
        session_gen = get_session()
        session = next(session_gen)

        try:
            penny_stocks = (
                session.query(PennyStockWatch)
                .filter(PennyStockWatch.is_active == True)  # type: ignore[arg-type]
                .all()
            )
            return [ps.symbol for ps in penny_stocks]  # type: ignore[attr-defined]
        finally:
            session.close()

    async def update_watchlist(self, candidates: List[PennyStockCandidate]) -> None:
        """Update database with penny stock candidates."""
        session_gen = get_session()
        session = next(session_gen)

        try:
            for candidate in candidates:
                # Check if already exists
                existing = (
                    session.query(PennyStockWatch)
                    .filter(PennyStockWatch.symbol == candidate.symbol)
                    .first()
                )

                if existing:
                    # Update existing
                    existing.current_price = candidate.current_price  # type: ignore[attr-defined]
                    existing.market_cap = candidate.market_cap  # type: ignore[attr-defined]
                    existing.volatility_30d = candidate.volatility_30d  # type: ignore[attr-defined]
                    existing.volatility_score = candidate.volatility_score  # type: ignore[attr-defined]
                    existing.sector = candidate.sector  # type: ignore[attr-defined]
                    existing.exchange = candidate.exchange  # type: ignore[attr-defined]
                    existing.last_updated = datetime.now()  # type: ignore[attr-defined]
                else:
                    # Create new
                    penny_stock = PennyStockWatch(
                        symbol=candidate.symbol,
                        current_price=candidate.current_price,
                        market_cap=candidate.market_cap,
                        volatility_30d=candidate.volatility_30d,
                        volatility_score=candidate.volatility_score,
                        sector=candidate.sector,
                        exchange=candidate.exchange,
                    )
                    session.add(penny_stock)

            session.commit()

        except Exception as e:
            session.rollback()
            self.logger.error(f"Failed to update penny watch list: {e}")
        finally:
            session.close()
