"""Portfolio performance analysis and reporting."""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from ...config.logging import get_logger
from ...core.stock_query import get_stock_price
from ...ormdb.database import get_session
from ...ormdb.penny_stock_models import (
    SpeculationPortfolio,
    VirtualPosition,
    VirtualTrade,
)
from .models import PerformanceReport, PortfolioSummary, PositionSummary

logger = get_logger(__name__)


class PerformanceAnalyzer:
    """Analyzes portfolio performance and generates reports."""

    def __init__(self, default_starting_balance: Decimal):
        self.logger = logger.bind(component="performance_analyzer")
        self.default_starting_balance = default_starting_balance

    async def get_portfolio_performance(
        self, portfolio_id: int
    ) -> Optional[PerformanceReport]:
        """
        Get comprehensive portfolio performance report.

        Args:
            portfolio_id: Portfolio ID

        Returns:
            PerformanceReport or None if portfolio not found
        """
        session_gen = get_session()
        session = next(session_gen)

        try:
            portfolio = (
                session.query(SpeculationPortfolio)
                .filter(
                    SpeculationPortfolio.id == portfolio_id,
                    SpeculationPortfolio.is_active == True,
                )
                .first()
            )

            if not portfolio:
                return None

            # Get current positions
            positions = (
                session.query(VirtualPosition)
                .filter(
                    VirtualPosition.portfolio_id == portfolio_id,
                    VirtualPosition.is_closed == False,
                )
                .all()
            )

            # Update position values with current prices
            position_summaries = []
            total_position_value = Decimal("0")

            for position in positions:
                try:
                    # Get current price
                    price_info = get_stock_price(position.symbol)  # type: ignore
                    current_price = Decimal(str(price_info.current_price))
                    current_value = current_price * position.quantity

                    # Update position
                    position.current_value = current_value  # type: ignore
                    position.unrealized_pnl = current_value - position.total_cost  # type: ignore
                    position.unrealized_pnl_pct = float(  # type: ignore
                        (position.unrealized_pnl / position.total_cost) * 100  # type: ignore
                    )
                    position.last_updated = datetime.now()  # type: ignore

                    total_position_value += current_value

                    # Create summary
                    position_summary = PositionSummary(
                        symbol=position.symbol,  # type: ignore
                        quantity=position.quantity,  # type: ignore
                        avg_cost_basis=position.avg_cost_basis,  # type: ignore
                        current_price=current_price,
                        current_value=current_value,  # type: ignore
                        unrealized_pnl=position.unrealized_pnl,  # type: ignore
                        unrealized_pnl_pct=position.unrealized_pnl_pct,  # type: ignore
                        position_pct=0.0,  # Will calculate after total value known
                    )
                    position_summaries.append(position_summary)

                except Exception as e:
                    self.logger.warning(
                        f"Failed to update price for {position.symbol}: {e}"
                    )
                    continue

            # Update portfolio totals
            portfolio.total_value = portfolio.virtual_balance + total_position_value  # type: ignore
            portfolio.total_invested = sum(pos.total_cost for pos in positions)  # type: ignore
            if portfolio.total_invested > 0:  # type: ignore
                portfolio.total_return_pct = float(  # type: ignore
                    (
                        (portfolio.total_value - self.default_starting_balance)  # type: ignore
                        / self.default_starting_balance
                    )
                    * 100
                )

            # Calculate position percentages
            for pos_summary in position_summaries:
                pos_summary.position_pct = (
                    float((pos_summary.current_value / portfolio.total_value) * 100)
                    if portfolio.total_value > 0  # type: ignore
                    else 0.0
                )

            # Get recent trades
            recent_trades = (
                session.query(VirtualTrade)
                .filter(VirtualTrade.portfolio_id == portfolio_id)
                .order_by(VirtualTrade.executed_at.desc())
                .limit(10)
                .all()
            )

            # Calculate risk metrics
            risk_metrics = self._calculate_risk_metrics(portfolio, position_summaries)

            # Create portfolio summary
            largest_position_pct = max(
                [pos.position_pct for pos in position_summaries], default=0.0
            )

            portfolio_summary = PortfolioSummary(
                portfolio_id=portfolio.id,  # type: ignore
                portfolio_name=portfolio.portfolio_name,  # type: ignore
                total_value=portfolio.total_value,  # type: ignore
                cash_balance=portfolio.virtual_balance,  # type: ignore
                invested_amount=portfolio.total_invested,  # type: ignore
                total_return_pct=portfolio.total_return_pct,  # type: ignore
                daily_return_pct=0.0,  # Would need historical data
                num_positions=len(position_summaries),
                largest_position_pct=largest_position_pct,
                risk_score=risk_metrics.get("risk_score", 5),
            )

            # Get daily performance (placeholder)
            daily_performance = []  # Would query PortfolioPerformance table

            session.commit()

            return PerformanceReport(
                portfolio_summary=portfolio_summary,
                positions=position_summaries,
                recent_trades=[self._trade_to_dict(trade) for trade in recent_trades],
                daily_performance=daily_performance,
                risk_metrics=risk_metrics,
            )

        except Exception as e:
            session.rollback()
            self.logger.error(f"Failed to get portfolio performance: {e}")
            return None
        finally:
            session.close()

    async def update_portfolio_metrics(self, portfolio_id: int) -> None:
        """Update portfolio performance metrics."""
        # This would update the portfolio's calculated metrics
        # Implementation would recalculate total_value, returns, etc.
        pass

    def _calculate_risk_metrics(
        self, portfolio, positions: List[PositionSummary]
    ) -> Dict:
        """Calculate risk metrics for portfolio."""
        # Simplified risk calculation
        risk_score = 5  # Default medium risk

        if positions:
            # Higher risk if concentrated in few positions
            if len(positions) <= 2:
                risk_score += 2

            # Higher risk if large position sizes
            max_position_pct = max([pos.position_pct for pos in positions])
            if max_position_pct > 50:
                risk_score += 2
            elif max_position_pct > 30:
                risk_score += 1

        return {
            "risk_score": min(10, max(1, risk_score)),
            "concentration_risk": max(
                [pos.position_pct for pos in positions], default=0
            ),
            "portfolio_beta": None,  # Would need market correlation data
        }

    def _trade_to_dict(self, trade: VirtualTrade) -> Dict:
        """Convert trade to dictionary."""
        return {
            "symbol": trade.symbol,
            "action": trade.action,
            "quantity": trade.quantity,
            "price_per_share": float(trade.price_per_share),  # type: ignore
            "total_amount": float(trade.total_amount),  # type: ignore
            "executed_at": trade.executed_at.isoformat(),
        }
