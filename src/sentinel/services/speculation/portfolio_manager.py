"""Portfolio creation and management."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from ...config.logging import get_logger
from ...ormdb.database import get_session
from ...ormdb.penny_stock_models import (
    PortfolioPerformance,
    SpeculationPortfolio,
    VirtualPosition,
)
from .models import PortfolioSummary

logger = get_logger(__name__)


class PortfolioManager:
    """Manages virtual portfolio creation and user portfolio queries."""

    def __init__(self, default_starting_balance: Decimal):
        self.logger = logger.bind(component="portfolio_manager")
        self.default_starting_balance = default_starting_balance

    async def create_virtual_portfolio(
        self,
        user_id: str,
        portfolio_name: str,
        starting_balance: Optional[Decimal] = None,
        strategy_type: Optional[str] = None,
        description: Optional[str] = None,
    ) -> int:
        """
        Create a new virtual trading portfolio.

        Args:
            user_id: User identifier (chat ID, etc.)
            portfolio_name: Name for the portfolio
            starting_balance: Starting virtual balance (default $10,000)
            strategy_type: Portfolio strategy ("aggressive", "conservative", etc.)
            description: Portfolio description

        Returns:
            Portfolio ID
        """
        if starting_balance is None:
            starting_balance = self.default_starting_balance

        session_gen = get_session()
        session = next(session_gen)

        try:
            # Check for duplicate names for this user
            existing = (
                session.query(SpeculationPortfolio)
                .filter(
                    SpeculationPortfolio.user_id == user_id,
                    SpeculationPortfolio.portfolio_name == portfolio_name,
                    SpeculationPortfolio.is_active == True,
                )
                .first()
            )

            if existing:
                raise ValueError(
                    f"Portfolio '{portfolio_name}' already exists for user"
                )

            # Create portfolio
            portfolio = SpeculationPortfolio(
                user_id=user_id,
                portfolio_name=portfolio_name,
                virtual_balance=starting_balance,
                total_value=starting_balance,
                strategy_type=strategy_type,
                description=description,
            )

            session.add(portfolio)
            session.commit()

            # Create initial performance snapshot
            self._create_performance_snapshot(portfolio.id, session)  # type: ignore

            self.logger.info(
                "Created virtual portfolio",
                user_id=user_id,
                portfolio_name=portfolio_name,
                starting_balance=float(starting_balance),
            )

            return portfolio.id  # type: ignore

        except Exception as e:
            session.rollback()
            self.logger.error(f"Failed to create portfolio: {e}")
            raise
        finally:
            session.close()

    async def get_user_portfolios(self, user_id: str) -> List[PortfolioSummary]:
        """
        Get all portfolios for a user.

        Args:
            user_id: User identifier

        Returns:
            List of portfolio summaries
        """
        session_gen = get_session()
        session = next(session_gen)

        try:
            portfolios = (
                session.query(SpeculationPortfolio)
                .filter(
                    SpeculationPortfolio.user_id == user_id,
                    SpeculationPortfolio.is_active == True,
                )
                .all()
            )

            summaries = []
            for portfolio in portfolios:
                # Get basic metrics
                num_positions = (
                    session.query(VirtualPosition)
                    .filter(
                        VirtualPosition.portfolio_id == portfolio.id,
                        VirtualPosition.is_closed == False,
                    )
                    .count()
                )

                summary = PortfolioSummary(
                    portfolio_id=portfolio.id,  # type: ignore
                    portfolio_name=portfolio.portfolio_name,  # type: ignore
                    total_value=portfolio.total_value,  # type: ignore
                    cash_balance=portfolio.virtual_balance,  # type: ignore
                    invested_amount=portfolio.total_invested,  # type: ignore
                    total_return_pct=portfolio.total_return_pct,  # type: ignore
                    daily_return_pct=0.0,  # Would need historical calculation
                    num_positions=num_positions,
                    largest_position_pct=0.0,  # Would need position analysis
                    risk_score=5,  # Default risk score
                )
                summaries.append(summary)

            return summaries

        except Exception as e:
            self.logger.error(f"Failed to get user portfolios: {e}")
            return []
        finally:
            session.close()

    def _create_performance_snapshot(self, portfolio_id: int, session) -> None:
        """Create initial performance snapshot for new portfolio."""
        portfolio = (
            session.query(SpeculationPortfolio)
            .filter(SpeculationPortfolio.id == portfolio_id)
            .first()
        )

        if portfolio:
            snapshot = PortfolioPerformance(
                portfolio_id=portfolio_id,
                snapshot_date=datetime.now().strftime("%Y-%m-%d"),
                total_value=portfolio.total_value,
                cash_balance=portfolio.virtual_balance,
                invested_amount=Decimal("0"),
                num_positions=0,
            )
            session.add(snapshot)
