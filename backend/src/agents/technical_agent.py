"""
Technical Analysis Agent.

Analyzes price data to generate trading signals.
Uses yfinance for data and ta for indicators if available.
"""

import logging
from typing import Any, Dict

import numpy as np

from src.connectors.base_connector import ensure_ns_suffix

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance not installed. Technical agent requires it for real market data.")

try:
    import ta
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False
    logger.warning("ta library not installed. Technical agent will use simplified calculations.")


class TechnicalAgent:
    """
    Analyzes technical indicators (RSI, SMA, MACD).
    """

    def __init__(self):
        pass

    def analyze(self, ticker: str) -> Dict[str, Any]:
        """
        Perform technical analysis on a ticker.

        Args:
            ticker: Stock symbol

        Returns:
            Dict with signal, score, and indicators
        """
        hist = self._get_price_data(ticker)
        
        if hist.empty:
            return self._neutral_response("No price data available")

        if len(hist) < 2:
            return self._neutral_response("Insufficient data")

        # Calculate indicators
        rsi = self._calculate_rsi(hist["Close"])
        sma_20 = self._calculate_sma(hist["Close"], 20)
        sma_50 = self._calculate_sma(hist["Close"], 50)
        
        current_price = hist["Close"].iloc[-1]
        current_rsi = rsi.iloc[-1] if hasattr(rsi, "iloc") else rsi
        current_sma_20 = sma_20.iloc[-1] if hasattr(sma_20, "iloc") else sma_20
        current_sma_50 = sma_50.iloc[-1] if hasattr(sma_50, "iloc") else sma_50

        # Generate signal
        score = 0.0
        signals = []

        # RSI Strategy
        if current_rsi < 30:
            score += 0.4
            signals.append(f"Oversold RSI ({current_rsi:.1f})")
        elif current_rsi > 70:
            score -= 0.4
            signals.append(f"Overbought RSI ({current_rsi:.1f})")

        # Trend Strategy
        if current_price > current_sma_20 > current_sma_50:
            score += 0.3
            signals.append("Bullish trend (Price > SMA20 > SMA50)")
        elif current_price < current_sma_20 < current_sma_50:
            score -= 0.3
            signals.append("Bearish trend (Price < SMA20 < SMA50)")

        # Normalize score
        score = max(-1.0, min(1.0, score))

        return {
            "signal": "BUY" if score > 0.2 else "SELL" if score < -0.2 else "HOLD",
            "technical_score": score,
            "indicators": {
                "rsi": float(current_rsi),
                "sma_20": float(current_sma_20),
                "sma_50": float(current_sma_50),
                "price": float(current_price)
            },
            "key_signals": signals or ["Neutral technicals"]
        }

    def _get_price_data(self, ticker: str) -> Any:
        """Fetch price data via NSE connector (uses 15-min cache)."""
        import pandas as pd

        try:
            from src.connectors.nse_connector import get_nse_connector
            nse = get_nse_connector()
            hist = nse.get_historical_data(ticker, period="3mo")
            if not hist.empty:
                return hist
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")

        logger.warning(f"No price data available for {ticker}")
        return pd.DataFrame()

    def _calculate_rsi(self, series: Any, window: int = 14) -> Any:
        """Calculate RSI."""
        if TA_AVAILABLE:
            from ta.momentum import RSIIndicator
            return RSIIndicator(close=series, window=window).rsi()
            
        # Manual calculation
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_sma(self, series: Any, window: int) -> Any:
        """Calculate SMA."""
        if TA_AVAILABLE:
            from ta.trend import SMAIndicator
            return SMAIndicator(close=series, window=window).sma_indicator()
            
        return series.rolling(window=window).mean()

    def _neutral_response(self, reason: str) -> Dict[str, Any]:
        return {
            "signal": "HOLD",
            "technical_score": 0.0,
            "indicators": {},
            "key_signals": [reason]
        }
