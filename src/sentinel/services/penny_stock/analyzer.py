"""Volatility analysis for penny stocks."""

from datetime import datetime
from typing import Optional

import yfinance as yf

from ...config.logging import get_logger
from .models import VolatilityMetrics

logger = get_logger(__name__)


class VolatilityAnalyzer:
    """Analyzes volatility metrics for penny stocks."""

    def __init__(self):
        self.logger = logger.bind(component="volatility_analyzer")

    async def get_volatility_metrics(self, symbol: str) -> Optional[VolatilityMetrics]:
        """
        Get comprehensive volatility analysis for a symbol.

        Args:
            symbol: Stock symbol to analyze

        Returns:
            VolatilityMetrics or None if analysis fails
        """
        try:
            self.logger.info(f"Analyzing volatility metrics for {symbol}")

            # Get historical data
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="30d", interval="1d")

            if hist.empty:
                self.logger.warning(f"No historical data for {symbol}")
                return None

            # Calculate daily returns
            daily_returns = hist["Close"].pct_change().dropna()

            if len(daily_returns) < 5:
                self.logger.warning(f"Insufficient data for {symbol}")
                return None

            # Calculate metrics
            current_price = float(hist["Close"].iloc[-1])
            volatility_30d = float(daily_returns.std() * (252**0.5))  # Annualized
            avg_daily_move = float(abs(daily_returns).mean() * 100)

            # Price range
            price_min = float(hist["Close"].min())
            price_max = float(hist["Close"].max())

            # Volume analysis
            volume_data = hist["Volume"].dropna()
            volume_volatility = (
                float(volume_data.std() / volume_data.mean())
                if len(volume_data) > 1
                else 0.0
            )

            # Find last spike (>20% move)
            large_moves = daily_returns[abs(daily_returns) > 0.20]
            last_spike_date = (
                large_moves.index[-1].to_pydatetime() if len(large_moves) > 0 else None
            )

            # Calculate volatility score (1-10)
            volatility_score = self._calculate_volatility_score(
                volatility_30d, avg_daily_move
            )

            return VolatilityMetrics(
                symbol=symbol,
                current_price=current_price,
                volatility_30d=volatility_30d,
                volatility_score=volatility_score,
                beta=None,  # Would need market data for beta calculation
                volume_volatility=volume_volatility,
                price_range_30d=(price_min, price_max),
                avg_daily_move=avg_daily_move,
                last_spike_date=last_spike_date,
            )

        except Exception as e:
            self.logger.error(f"Failed to analyze volatility for {symbol}: {e}")
            return None

    def _calculate_volatility_score(
        self, volatility_30d: float, avg_daily_move: float
    ) -> int:
        """
        Calculate volatility score from 1-10.

        Args:
            volatility_30d: Annualized volatility
            avg_daily_move: Average daily percentage move

        Returns:
            Score from 1 (boring) to 10 (extremely volatile)
        """
        # Combine volatility and daily move metrics
        # High volatility (>100%) = exciting penny stock
        # Low volatility (<20%) = boring penny stock

        # Normalize volatility (0-200% -> 0-10 scale)
        vol_score = min(volatility_30d * 5, 10)

        # Normalize daily move (0-10% -> 0-10 scale)
        move_score = min(avg_daily_move, 10)

        # Weighted combination
        combined_score = (vol_score * 0.7) + (move_score * 0.3)

        return max(1, min(10, int(round(combined_score))))
