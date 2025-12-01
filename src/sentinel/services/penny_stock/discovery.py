"""Penny stock discovery and screening operations."""

from typing import List, Optional

import yfinance as yf

from ...config.logging import get_logger
from .analyzer import VolatilityAnalyzer
from .models import PennyStockCandidate, ScreeningCriteria

logger = get_logger(__name__)


class PennyStockDiscovery:
    """Handles penny stock discovery and screening."""

    # Common penny stock symbols to start monitoring
    WATCHLIST_SEEDS = [
        # Biotech/pharma penny stocks
        "SNDL",
        "ATOS",
        "JAGX",
        "CIDM",
        "SENS",
        "GNUS",
        "SHIP",
        "CTRM",
        # Mining/energy
        "NRGU",
        "BOIL",
        "DGAZ",
        "KOLD",
        "ERY",
        "DRIP",
        "GUSH",
        "GASL",
        # Tech/meme potentials
        "BB",
        "NOK",
        "SIRI",
        "PLTR",
        "WISH",
        "CLOV",
        "SOFI",
        "HOOD",
    ]

    def __init__(self, volatility_analyzer: VolatilityAnalyzer):
        self.volatility_analyzer = volatility_analyzer
        self.logger = logger.bind(component="penny_stock_discovery")

    async def discover_penny_stocks(
        self,
        criteria: Optional[ScreeningCriteria] = None,
        max_stocks: int = 50,
        existing_symbols: Optional[List[str]] = None,
    ) -> List[PennyStockCandidate]:
        """
        Discover trending penny stocks based on criteria.

        Args:
            criteria: Screening criteria (default applied if None)
            max_stocks: Maximum number of stocks to return
            existing_symbols: Additional symbols to check

        Returns:
            List of penny stock candidates sorted by interest score
        """
        if criteria is None:
            criteria = ScreeningCriteria()

        self.logger.info("Starting penny stock discovery", max_stocks=max_stocks)

        candidates = []

        # Start with seed watchlist and expand
        symbols_to_check = self.WATCHLIST_SEEDS.copy()

        # Add any existing penny stocks from our watch table
        if existing_symbols:
            symbols_to_check.extend(existing_symbols)

        # Remove duplicates
        symbols_to_check = list(set(symbols_to_check))

        # Screen each symbol
        for symbol in symbols_to_check:
            try:
                candidate = await self._evaluate_penny_candidate(symbol, criteria)
                if candidate:
                    candidates.append(candidate)
            except Exception as e:
                self.logger.warning(f"Failed to evaluate {symbol}: {e}")
                continue

        # Sort by interest score (combination of volatility and volume surge)
        candidates.sort(
            key=lambda x: (x.volatility_score * 0.7 + x.volume_surge_ratio * 0.3),
            reverse=True,
        )

        # Limit results
        candidates = candidates[:max_stocks]

        self.logger.info(
            "Penny stock discovery completed",
            candidates_found=len(candidates),
            top_volatility=candidates[0].volatility_score if candidates else 0,
        )

        return candidates

    async def screen_by_criteria(
        self, criteria: ScreeningCriteria, existing_symbols: Optional[List[str]] = None
    ) -> List[PennyStockCandidate]:
        """
        Screen stocks by specific criteria.

        Args:
            criteria: Detailed screening criteria
            existing_symbols: Additional symbols to check

        Returns:
            List of matching penny stock candidates
        """
        return await self.discover_penny_stocks(
            criteria, existing_symbols=existing_symbols
        )

    async def evaluate_candidate(
        self, symbol: str, criteria: Optional[ScreeningCriteria] = None
    ) -> Optional[PennyStockCandidate]:
        """
        Evaluate if a symbol qualifies as penny stock candidate.

        Args:
            symbol: Stock symbol to evaluate
            criteria: Screening criteria (default if None)

        Returns:
            PennyStockCandidate or None if doesn't qualify
        """
        if criteria is None:
            criteria = ScreeningCriteria()

        return await self._evaluate_penny_candidate(symbol, criteria)

    async def _evaluate_penny_candidate(
        self, symbol: str, criteria: ScreeningCriteria
    ) -> Optional[PennyStockCandidate]:
        """Evaluate if a symbol qualifies as penny stock candidate."""
        try:
            ticker = yf.Ticker(symbol)

            # Get current price and basic info
            try:
                current_price = float(ticker.fast_info.last_price)
            except (AttributeError, ValueError, TypeError) as e:
                # Fallback to history
                logger.debug(
                    f"Could not get fast_info for {symbol}, using history: {e}"
                )
                hist = ticker.history(period="1d")
                if hist.empty:
                    return None
                current_price = float(hist["Close"].iloc[-1])

            # Check price criteria
            if current_price > criteria.max_price:
                return None

            # Get additional data
            info = ticker.info
            volume = info.get("volume", 0)
            avg_volume = info.get("averageVolume", volume)
            market_cap = info.get("marketCap")
            sector = info.get("sector", "Unknown")

            # Check volume criteria
            if volume < criteria.min_volume:
                return None

            # Check market cap criteria
            if (
                criteria.min_market_cap
                and market_cap
                and market_cap < criteria.min_market_cap
            ):
                return None
            if (
                criteria.max_market_cap
                and market_cap
                and market_cap > criteria.max_market_cap
            ):
                return None

            # Calculate metrics
            volatility_metrics = await self.volatility_analyzer.get_volatility_metrics(
                symbol
            )
            volatility_30d = (
                volatility_metrics.volatility_30d if volatility_metrics else 0.0
            )
            volatility_score = (
                volatility_metrics.volatility_score if volatility_metrics else 1
            )

            # Check volatility criteria
            if (
                volatility_score < criteria.min_volatility_score
                or volatility_score > criteria.max_volatility_score
            ):
                return None

            volume_surge_ratio = volume / avg_volume if avg_volume > 0 else 1.0

            # Check volume surge criteria
            if volume_surge_ratio < criteria.volume_surge_min:
                return None

            # Calculate 24h price change
            hist = ticker.history(period="2d")
            price_change_24h = 0.0
            if len(hist) >= 2:
                prev_close = float(hist["Close"].iloc[-2])
                price_change_24h = ((current_price - prev_close) / prev_close) * 100

            return PennyStockCandidate(
                symbol=symbol,
                current_price=current_price,
                market_cap=market_cap,
                volume=volume,
                avg_volume=avg_volume,
                sector=sector,
                volatility_30d=volatility_30d,
                volatility_score=volatility_score,
                volume_surge_ratio=volume_surge_ratio,
                price_change_24h=price_change_24h,
                exchange=info.get("exchange", "Unknown"),
            )

        except Exception as e:
            self.logger.warning(f"Failed to evaluate {symbol}: {e}")
            return None
