"""Quiver API client for congressional trading data."""

from datetime import datetime
from typing import List, Optional

import pandas as pd
from quiverquant import quiver

from ...config.logging import get_logger
from .models import CongressionalTrade

logger = get_logger(__name__)


class QuiverAPIClient:
    """Client for Quiver Quantitative API."""

    def __init__(self, api_token: str):
        """
        Initialize Quiver API client.

        Args:
            api_token: Quiver Quantitative API token
        """
        self.api_token = api_token
        self.quiver_client = quiver(api_token)
        self.logger = logger.bind(component="quiver_api_client")

    async def get_house_trades(
        self,
        representative: Optional[str],
        ticker: Optional[str],
        start_date: datetime,
    ) -> List[CongressionalTrade]:
        """
        Get House trading data.

        Args:
            representative: Specific representative name (optional)
            ticker: Specific stock ticker (optional)
            start_date: Start date for filtering trades

        Returns:
            List of CongressionalTrade objects
        """
        try:
            # Get House trading data
            house_data = self.quiver_client.house_trading()

            if house_data is not None and not house_data.empty:
                trades = self._parse_trading_data(house_data, "House", start_date)

                # Filter by representative if specified
                if representative:
                    trades = [
                        t
                        for t in trades
                        if representative.lower() in t.representative.lower()
                    ]

                # Filter by ticker if specified
                if ticker:
                    trades = [t for t in trades if t.ticker.upper() == ticker.upper()]

                return trades

            return []

        except Exception as e:
            self.logger.warning("Failed to fetch House trades", error=str(e))
            return []

    async def get_senate_trades(
        self,
        representative: Optional[str],
        ticker: Optional[str],
        start_date: datetime,
    ) -> List[CongressionalTrade]:
        """
        Get Senate trading data.

        Args:
            representative: Specific representative name (optional)
            ticker: Specific stock ticker (optional)
            start_date: Start date for filtering trades

        Returns:
            List of CongressionalTrade objects
        """
        try:
            # Get Senate trading data
            senate_data = self.quiver_client.senate_trading()

            if senate_data is not None and not senate_data.empty:
                trades = self._parse_trading_data(senate_data, "Senate", start_date)

                # Filter by representative if specified
                if representative:
                    trades = [
                        t
                        for t in trades
                        if representative.lower() in t.representative.lower()
                    ]

                # Filter by ticker if specified
                if ticker:
                    trades = [t for t in trades if t.ticker.upper() == ticker.upper()]

                return trades

            return []

        except Exception as e:
            self.logger.warning("Failed to fetch Senate trades", error=str(e))
            return []

    def _parse_trading_data(
        self, data: pd.DataFrame, source: str, start_date: datetime
    ) -> List[CongressionalTrade]:
        """
        Parse trading data from DataFrame to CongressionalTrade objects.

        Args:
            data: DataFrame containing trading data
            source: Data source ("House" or "Senate")
            start_date: Start date for filtering trades

        Returns:
            List of CongressionalTrade objects
        """
        trades = []

        for _, row in data.iterrows():
            try:
                # Parse transaction date
                date_value = row.get("Date") or row.get("TransactionDate")
                if date_value is None:
                    continue

                transaction_date = pd.to_datetime(date_value, errors="coerce")
                if transaction_date is None or pd.isna(transaction_date):
                    continue

                # Skip trades before start_date
                if transaction_date < start_date:
                    continue

                # Extract trade information
                representative = row.get(
                    "Representative", row.get("Senator", "Unknown")
                )
                ticker = row.get("Ticker", row.get("Symbol", ""))
                transaction_type = row.get("Transaction", row.get("Type", "Unknown"))
                amount = row.get("Amount", row.get("Range", "Unknown"))

                # Handle report date if available
                report_date = None
                report_date_value = row.get("ReportDate")
                if report_date_value is not None:
                    report_date = pd.to_datetime(report_date_value, errors="coerce")

                asset_description = row.get("AssetDescription", row.get("Description"))

                trade = CongressionalTrade(
                    representative=representative,
                    transaction_date=transaction_date.to_pydatetime(),
                    ticker=ticker,
                    transaction_type=transaction_type,
                    amount=amount,
                    source=source,
                    report_date=(
                        report_date.to_pydatetime()
                        if report_date is not None and not pd.isna(report_date)
                        else None
                    ),
                    asset_description=asset_description,
                )

                trades.append(trade)

            except Exception as e:
                self.logger.warning(
                    "Failed to parse trade row",
                    error=str(e),
                    row_data=row.to_dict() if hasattr(row, "to_dict") else str(row),
                )

        return trades
