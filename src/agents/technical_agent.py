"""
Technical Analysis Agent.

Analyzes price data to generate trading signals.
Uses yfinance for data and ta for indicators if available.
"""

import logging
from typing import Any, Dict

import numpy as np

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance not installed. Technical agent will use mock data.")

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
        """Fetch price data or return mock."""
        import pandas as pd
        
        if YFINANCE_AVAILABLE:
            try:
                # Download minimal data for speed
                ticker_obj = yf.Ticker(ticker)
                hist = ticker_obj.history(period="3mo", interval="1d")
                if not hist.empty:
                    return hist
            except Exception as e:
                logger.error(f"Error fetching data for {ticker}: {e}")

        # Mock data fallback
        logger.info(f"Using mock data for {ticker}")
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100)
        
        # Generate random walk with a bias to create trends for demo
        # Use simple hash of ticker to decide trend direction so it's consistent
        seed = sum(ord(c) for c in ticker)
        np.random.seed(seed)
        
        trend = np.random.choice([-0.5, 0.0, 0.5]) # Bias
        
        prices = [150.0]
        for _ in range(99):
            change = np.random.normal(trend, 2.0)
            prices.append(max(10.0, prices[-1] + change))
            
        data = pd.DataFrame(index=dates)
        data["Close"] = prices
        data["High"] = [p + 2 for p in prices]
        data["Low"] = [p - 2 for p in prices]
        data["Volume"] = 1000000
        
        return data

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
