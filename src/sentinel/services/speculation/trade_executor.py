"""Trade execution logic for buy and sell operations."""

from datetime import datetime
from decimal import Decimal
from typing import Dict

from ...config.logging import get_logger
from ...core.stock_query import get_stock_price
from ...ormdb.database import get_session
from ...ormdb.penny_stock_models import (
    SpeculationPortfolio,
    VirtualPosition,
    VirtualTrade,
)
from .models import TradeRequest, TradeResult

logger = get_logger(__name__)


class TradeExecutor:
    """Executes virtual buy and sell trades."""

    def __init__(self, transaction_fee: Decimal):
        self.logger = logger.bind(component="trade_executor")
        self.transaction_fee = transaction_fee

    async def execute_virtual_trade(self, trade_request: TradeRequest) -> TradeResult:
        """
        Execute a virtual trade (buy or sell).

        Args:
            trade_request: Trade request details

        Returns:
            TradeResult with execution details
        """
        session_gen = get_session()
        session = next(session_gen)

        try:
            # Get portfolio
            portfolio = (
                session.query(SpeculationPortfolio)
                .filter(
                    SpeculationPortfolio.id == trade_request.portfolio_id,
                    SpeculationPortfolio.is_active == True,
                )
                .first()
            )

            if not portfolio:
                return TradeResult(
                    success=False,
                    trade_id=None,
                    executed_price=None,
                    total_amount=None,
                    new_position=None,
                    error_message="Portfolio not found",
                    portfolio_balance=Decimal("0"),
                )

            # Get current stock price
            try:
                price_info = get_stock_price(trade_request.symbol)
                current_price = Decimal(str(price_info.current_price))
            except Exception as e:
                return TradeResult(
                    success=False,
                    trade_id=None,
                    executed_price=None,
                    total_amount=None,
                    new_position=None,
                    error_message=f"Failed to get price for {trade_request.symbol}",
                    portfolio_balance=portfolio.virtual_balance,  # type: ignore
                )

            # Execute based on action
            if trade_request.action.upper() == "BUY":
                result = await self._execute_buy_trade(
                    session, portfolio, trade_request, current_price
                )
            elif trade_request.action.upper() == "SELL":
                result = await self._execute_sell_trade(
                    session, portfolio, trade_request, current_price
                )
            else:
                return TradeResult(
                    success=False,
                    trade_id=None,
                    executed_price=None,
                    total_amount=None,
                    new_position=None,
                    error_message=f"Invalid action: {trade_request.action}",
                    portfolio_balance=portfolio.virtual_balance,  # type: ignore
                )

            if result.success:
                session.commit()

                self.logger.info(
                    "Executed virtual trade",
                    portfolio_id=trade_request.portfolio_id,
                    symbol=trade_request.symbol,
                    action=trade_request.action,
                    quantity=trade_request.quantity,
                    price=(
                        float(result.executed_price) if result.executed_price else None
                    ),
                )
            else:
                session.rollback()

            return result

        except Exception as e:
            session.rollback()
            self.logger.error(f"Failed to execute trade: {e}")
            return TradeResult(
                success=False,
                trade_id=None,
                executed_price=None,
                total_amount=None,
                new_position=None,
                error_message=f"Trade execution error: {str(e)}",
                portfolio_balance=Decimal("0"),
            )
        finally:
            session.close()

    async def _execute_buy_trade(
        self,
        session,
        portfolio: SpeculationPortfolio,
        trade_request: TradeRequest,
        current_price: Decimal,
    ) -> TradeResult:
        """Execute a buy trade."""
        total_cost = (current_price * trade_request.quantity) + self.transaction_fee

        # Check if enough balance
        if portfolio.virtual_balance < total_cost:  # type: ignore
            return TradeResult(
                success=False,
                trade_id=None,
                executed_price=None,
                total_amount=None,
                new_position=None,
                error_message="Insufficient balance",
                portfolio_balance=portfolio.virtual_balance,  # type: ignore
            )

        # Create trade record
        trade = VirtualTrade(
            portfolio_id=portfolio.id,
            symbol=trade_request.symbol,
            action="BUY",
            quantity=trade_request.quantity,
            price_per_share=current_price,
            total_amount=total_cost,
            transaction_fee=self.transaction_fee,
        )
        session.add(trade)
        session.flush()  # Get trade ID

        # Update/create position
        position = (
            session.query(VirtualPosition)
            .filter(
                VirtualPosition.portfolio_id == portfolio.id,
                VirtualPosition.symbol == trade_request.symbol,
                VirtualPosition.is_closed == False,
            )
            .first()
        )

        if position:
            # Update existing position
            total_shares = position.quantity + trade_request.quantity
            total_cost_basis = position.total_cost + (
                current_price * trade_request.quantity
            )
            position.avg_cost_basis = total_cost_basis / total_shares
            position.quantity = total_shares
            position.total_cost = total_cost_basis
            position.last_updated = datetime.now()
        else:
            # Create new position
            position = VirtualPosition(
                portfolio_id=portfolio.id,
                symbol=trade_request.symbol,
                quantity=trade_request.quantity,
                avg_cost_basis=current_price,
                total_cost=current_price * trade_request.quantity,
            )
            session.add(position)

        # Update portfolio balance
        portfolio.virtual_balance -= total_cost  # type: ignore
        portfolio.last_updated = datetime.now()  # type: ignore

        return TradeResult(
            success=True,
            trade_id=trade.id,  # type: ignore
            executed_price=current_price,
            total_amount=total_cost,
            new_position=self._position_to_dict(position),
            error_message=None,
            portfolio_balance=portfolio.virtual_balance,  # type: ignore
        )

    async def _execute_sell_trade(
        self,
        session,
        portfolio: SpeculationPortfolio,
        trade_request: TradeRequest,
        current_price: Decimal,
    ) -> TradeResult:
        """Execute a sell trade."""
        # Find existing position
        position = (
            session.query(VirtualPosition)
            .filter(
                VirtualPosition.portfolio_id == portfolio.id,
                VirtualPosition.symbol == trade_request.symbol,
                VirtualPosition.is_closed == False,
            )
            .first()
        )

        if not position:
            return TradeResult(
                success=False,
                trade_id=None,
                executed_price=None,
                total_amount=None,
                new_position=None,
                error_message=f"No position found for {trade_request.symbol}",
                portfolio_balance=portfolio.virtual_balance,  # type: ignore
            )

        if position.quantity < trade_request.quantity:
            return TradeResult(
                success=False,
                trade_id=None,
                executed_price=None,
                total_amount=None,
                new_position=None,
                error_message=f"Insufficient shares (have {position.quantity}, want to sell {trade_request.quantity})",
                portfolio_balance=portfolio.virtual_balance,  # type: ignore
            )

        # Calculate proceeds
        gross_proceeds = current_price * trade_request.quantity
        net_proceeds = gross_proceeds - self.transaction_fee

        # Create trade record
        trade = VirtualTrade(
            portfolio_id=portfolio.id,
            symbol=trade_request.symbol,
            action="SELL",
            quantity=trade_request.quantity,
            price_per_share=current_price,
            total_amount=net_proceeds,
            transaction_fee=self.transaction_fee,
        )
        session.add(trade)
        session.flush()

        # Update position
        if position.quantity == trade_request.quantity:
            # Close position completely
            position.is_closed = True
            position.closed_at = datetime.now()
        else:
            # Partial sale - reduce quantity proportionally
            remaining_quantity = position.quantity - trade_request.quantity
            cost_reduction = (
                trade_request.quantity / position.quantity
            ) * position.total_cost

            position.quantity = remaining_quantity
            position.total_cost -= cost_reduction
            position.last_updated = datetime.now()

        # Update portfolio balance
        portfolio.virtual_balance += net_proceeds  # type: ignore
        portfolio.last_updated = datetime.now()  # type: ignore

        return TradeResult(
            success=True,
            trade_id=trade.id,  # type: ignore
            executed_price=current_price,
            total_amount=net_proceeds,
            new_position=self._position_to_dict(position),
            error_message=None,
            portfolio_balance=portfolio.virtual_balance,  # type: ignore
        )

    def _position_to_dict(self, position: VirtualPosition) -> Dict:
        """Convert position to dictionary."""
        return {
            "symbol": position.symbol,
            "quantity": position.quantity,
            "avg_cost_basis": float(position.avg_cost_basis),  # type: ignore
            "total_cost": float(position.total_cost),  # type: ignore
            "is_closed": position.is_closed,
        }
