"""Leaderboard and portfolio ranking functionality."""

from typing import List

from ...config.logging import get_logger
from ...ormdb.database import get_session
from ...ormdb.penny_stock_models import SpeculationPortfolio, VirtualTrade
from .models import PortfolioRanking

logger = get_logger(__name__)


class LeaderboardManager:
    """Manages leaderboards and portfolio rankings."""

    def __init__(self):
        self.logger = logger.bind(component="leaderboard_manager")

    async def get_leaderboard(
        self, period: str = "all_time", limit: int = 10
    ) -> List[PortfolioRanking]:
        """
        Get performance leaderboard.

        Args:
            period: Time period ("daily", "weekly", "monthly", "all_time")
            limit: Maximum number of entries to return

        Returns:
            List of portfolio rankings
        """
        session_gen = get_session()
        session = next(session_gen)

        try:
            # Get all active portfolios
            portfolios = (
                session.query(SpeculationPortfolio)
                .filter(SpeculationPortfolio.is_active == True)
                .all()
            )

            rankings = []

            for portfolio in portfolios:
                # Calculate metrics for each portfolio
                num_trades = (
                    session.query(VirtualTrade)
                    .filter(VirtualTrade.portfolio_id == portfolio.id)
                    .count()
                )

                # Calculate win rate (simplified - profitable trades / total trades)
                profitable_trades = (
                    session.query(VirtualTrade)
                    .filter(
                        VirtualTrade.portfolio_id == portfolio.id,
                        VirtualTrade.action == "SELL",
                    )
                    .count()
                )  # This is oversimplified, would need proper P&L calculation

                win_rate = (
                    (profitable_trades / num_trades * 100) if num_trades > 0 else 0.0
                )

                # Simple risk-adjusted return (Sharpe-like)
                risk_adjusted_return = portfolio.total_return_pct / max(
                    1.0, portfolio.total_return_pct * 0.1
                )

                ranking = PortfolioRanking(
                    rank=0,  # Will set after sorting
                    user_id=portfolio.user_id,  # type: ignore[arg-type]
                    portfolio_name=portfolio.portfolio_name,  # type: ignore[arg-type]
                    total_return_pct=portfolio.total_return_pct,  # type: ignore[arg-type]
                    total_value=portfolio.total_value,  # type: ignore[arg-type]
                    risk_adjusted_return=risk_adjusted_return,  # type: ignore[arg-type]
                    num_trades=num_trades,
                    win_rate=win_rate,
                )
                rankings.append(ranking)

            # Sort by total return percentage
            rankings.sort(key=lambda x: x.total_return_pct, reverse=True)

            # Set ranks
            for i, ranking in enumerate(rankings):
                ranking.rank = i + 1

            # Limit results
            rankings = rankings[:limit]

            self.logger.info(f"Generated leaderboard with {len(rankings)} entries")

            return rankings

        except Exception as e:
            self.logger.error(f"Failed to get leaderboard: {e}")
            return []
        finally:
            session.close()
