"""Data processing utilities for congressional trading data."""

from typing import List

from ...config.logging import get_logger
from .models import CongressionalActivity, CongressionalTrade

logger = get_logger(__name__)


class CongressionalDataProcessor:
    """Processor for congressional trading data analysis."""

    def __init__(self):
        self.logger = logger.bind(component="congressional_data_processor")

    def analyze_activity(
        self, representative: str, trades: List[CongressionalTrade], days_back: int
    ) -> CongressionalActivity:
        """
        Analyze trading activity for a specific congressional member.

        Args:
            representative: Name of the congressional member
            trades: List of trades to analyze
            days_back: Number of days the analysis covers

        Returns:
            CongressionalActivity analysis
        """
        # Analyze trading patterns
        buy_count = len([t for t in trades if "buy" in t.transaction_type.lower()])
        sale_count = len([t for t in trades if "sale" in t.transaction_type.lower()])

        active_tickers = list(set([t.ticker for t in trades if t.ticker]))

        last_activity_date = None
        if trades:
            last_activity_date = max(t.transaction_date for t in trades)

        activity = CongressionalActivity(
            representative=representative,
            recent_trades=trades,
            total_transactions=len(trades),
            buy_count=buy_count,
            sale_count=sale_count,
            active_tickers=active_tickers,
            analysis_period=f"{days_back} days",
            last_activity_date=last_activity_date,
        )

        self.logger.info(
            "Congressional activity analyzed",
            representative=representative,
            total_trades=len(trades),
            buy_count=buy_count,
            sale_count=sale_count,
            unique_tickers=len(active_tickers),
        )

        return activity

    def format_trade_summary(self, trade: CongressionalTrade) -> str:
        """
        Format a congressional trade for display.

        Args:
            trade: CongressionalTrade object

        Returns:
            Formatted string summary
        """
        return (
            f"{trade.representative} ({trade.source}) "
            f"{trade.transaction_type} {trade.ticker} "
            f"({trade.amount}) on {trade.transaction_date.strftime('%Y-%m-%d')}"
        )

    def get_notable_trades(
        self, trades: List[CongressionalTrade], min_amount_threshold: str = "$50,000"
    ) -> List[CongressionalTrade]:
        """
        Filter trades for notable/large transactions.

        Args:
            trades: List of trades to filter
            min_amount_threshold: Minimum amount to be considered notable

        Returns:
            List of notable trades
        """
        # This is a simple implementation - could be enhanced with proper amount parsing
        notable_trades = []

        for trade in trades:
            amount_str = trade.amount.upper()
            # Look for large amounts (this is a simplified check)
            if any(
                threshold in amount_str
                for threshold in ["$50,000", "$100,000", "$250,000", "$1,000,000"]
            ):
                notable_trades.append(trade)
            elif "OVER $" in amount_str:  # Catch "Over $1,000,000" type entries
                notable_trades.append(trade)

        return notable_trades
