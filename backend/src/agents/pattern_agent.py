"""
Chart Pattern Detection Agent.

Rule-based detection using ta library on yfinance .NS data.
Detects: Bollinger breakout, RSI divergence, MACD crossover,
volume breakout, support/resistance, golden/death cross.
"""
import logging
from typing import Any, Optional

import numpy as np
import pandas as pd

from src.connectors.base_connector import ensure_ns_suffix

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    import ta
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False


class PatternAgent:
    """Detects chart patterns on Indian stocks using technical indicators."""

    def detect_all(self, ticker: str, period: str = "6mo") -> list[dict[str, Any]]:
        """Run all pattern detectors on a stock. Returns list of detected patterns."""
        if not YFINANCE_AVAILABLE or not TA_AVAILABLE:
            return [{"pattern": "unavailable", "error": "yfinance or ta not installed"}]

        try:
            tk = yf.Ticker(ensure_ns_suffix(ticker))
            df = tk.history(period=period, interval="1d")
            if df.empty or len(df) < 30:
                return []
        except Exception as e:
            logger.error(f"Data fetch failed for {ticker}: {e}")
            return []

        patterns = []
        for detector in [
            self._detect_rsi_extreme,
            self._detect_rsi_divergence,
            self._detect_macd_crossover,
            self._detect_bollinger_breakout,
            self._detect_volume_breakout,
            self._detect_golden_death_cross,
            self._detect_trend_strength,
        ]:
            result = detector(df, ticker)
            if result:
                patterns.append(result)

        return patterns

    def _detect_rsi_divergence(self, df: pd.DataFrame, ticker: str) -> Optional[dict]:
        """Detect RSI divergence: price new high/low but RSI doesn't confirm."""
        rsi = ta.momentum.RSIIndicator(close=df["Close"], window=14).rsi()
        if len(rsi.dropna()) < 20:
            return None

        price = df["Close"]
        recent_price = price.iloc[-5:]
        recent_rsi = rsi.iloc[-5:]
        prior_price = price.iloc[-20:-5]
        prior_rsi = rsi.iloc[-20:-5]

        # Bullish divergence: price makes lower low, RSI makes higher low
        if recent_price.min() < prior_price.min() and recent_rsi.min() > prior_rsi.min():
            return {
                "pattern": "rsi_divergence",
                "direction": "bullish",
                "confidence": round(min(0.85, 0.5 + (prior_rsi.min() - recent_rsi.min()) / 100), 2),
                "explanation": f"Price made a lower low (₹{recent_price.min():.2f}) but RSI held higher ({recent_rsi.min():.1f} vs {prior_rsi.min():.1f}) — bullish divergence suggesting potential reversal",
                "current_rsi": round(float(rsi.iloc[-1]), 1),
                "ticker": ticker,
            }

        # Bearish divergence: price makes higher high, RSI makes lower high
        if recent_price.max() > prior_price.max() and recent_rsi.max() < prior_rsi.max():
            return {
                "pattern": "rsi_divergence",
                "direction": "bearish",
                "confidence": round(min(0.85, 0.5 + (prior_rsi.max() - recent_rsi.max()) / 100), 2),
                "explanation": f"Price made a higher high (₹{recent_price.max():.2f}) but RSI diverged lower ({recent_rsi.max():.1f} vs {prior_rsi.max():.1f}) — bearish divergence warning",
                "current_rsi": round(float(rsi.iloc[-1]), 1),
                "ticker": ticker,
            }
        return None

    def _detect_macd_crossover(self, df: pd.DataFrame, ticker: str) -> Optional[dict]:
        """Detect MACD line crossing signal line."""
        macd_ind = ta.trend.MACD(close=df["Close"])
        macd = macd_ind.macd()
        signal = macd_ind.macd_signal()
        hist = macd_ind.macd_diff()

        if len(hist.dropna()) < 5:
            return None

        # Check for crossover in last 3 days
        for i in range(-3, 0):
            if len(hist) + i < 1:
                continue
            prev_hist = hist.iloc[i - 1]
            curr_hist = hist.iloc[i]

            if pd.isna(prev_hist) or pd.isna(curr_hist):
                continue

            # Bullish crossover: histogram goes from negative to positive
            if prev_hist < 0 and curr_hist > 0:
                return {
                    "pattern": "macd_crossover",
                    "direction": "bullish",
                    "confidence": round(min(0.8, 0.5 + abs(curr_hist) * 10), 2),
                    "explanation": f"MACD crossed above signal line — bullish momentum building (histogram: {curr_hist:.4f})",
                    "ticker": ticker,
                }
            # Bearish crossover
            if prev_hist > 0 and curr_hist < 0:
                return {
                    "pattern": "macd_crossover",
                    "direction": "bearish",
                    "confidence": round(min(0.8, 0.5 + abs(curr_hist) * 10), 2),
                    "explanation": f"MACD crossed below signal line — bearish momentum (histogram: {curr_hist:.4f})",
                    "ticker": ticker,
                }
        return None

    def _detect_bollinger_breakout(self, df: pd.DataFrame, ticker: str) -> Optional[dict]:
        """Detect Bollinger Band squeeze then breakout."""
        bb = ta.volatility.BollingerBands(close=df["Close"], window=20, window_dev=2)
        upper = bb.bollinger_hband()
        lower = bb.bollinger_lband()
        width = bb.bollinger_wband()

        if len(width.dropna()) < 10:
            return None

        # Check for squeeze (narrow bands) followed by breakout
        recent_width = width.iloc[-5:].mean()
        prior_width = width.iloc[-20:-5].mean()
        price = df["Close"].iloc[-1]
        upper_val = upper.iloc[-1]
        lower_val = lower.iloc[-1]

        if prior_width == 0:
            return None

        squeeze_ratio = recent_width / prior_width

        if squeeze_ratio < 0.7:  # Bands narrowing (squeeze)
            if price > upper_val:
                return {
                    "pattern": "bollinger_breakout",
                    "direction": "bullish",
                    "confidence": round(min(0.85, 0.6 + (1 - squeeze_ratio) * 0.5), 2),
                    "explanation": f"Price (₹{price:.2f}) broke above upper Bollinger Band (₹{upper_val:.2f}) after a squeeze — bullish breakout",
                    "ticker": ticker,
                }
            if price < lower_val:
                return {
                    "pattern": "bollinger_breakout",
                    "direction": "bearish",
                    "confidence": round(min(0.85, 0.6 + (1 - squeeze_ratio) * 0.5), 2),
                    "explanation": f"Price (₹{price:.2f}) broke below lower Bollinger Band (₹{lower_val:.2f}) after a squeeze — bearish breakdown",
                    "ticker": ticker,
                }
        return None

    def _detect_volume_breakout(self, df: pd.DataFrame, ticker: str) -> Optional[dict]:
        """Detect volume spike > 2x 20-day average."""
        if "Volume" not in df.columns or len(df) < 20:
            return None

        avg_vol = df["Volume"].iloc[-21:-1].mean()
        today_vol = df["Volume"].iloc[-1]

        if avg_vol == 0:
            return None

        ratio = today_vol / avg_vol
        if ratio >= 2.0:
            prev_close = df["Close"].iloc[-2]
            if prev_close == 0 or pd.isna(prev_close):
                price_change = 0.0
            else:
                price_change = (df["Close"].iloc[-1] - prev_close) / prev_close * 100
            direction = "bullish" if price_change > 0 else "bearish"
            return {
                "pattern": "volume_breakout",
                "direction": direction,
                "confidence": round(min(0.9, 0.5 + (ratio - 2) * 0.1), 2),
                "explanation": f"Volume ({today_vol:,.0f}) is {ratio:.1f}x the 20-day average ({avg_vol:,.0f}) — {direction} volume breakout with {price_change:+.1f}% price move",
                "ticker": ticker,
                "volume_ratio": round(ratio, 1),
            }
        return None

    def _detect_rsi_extreme(self, df: pd.DataFrame, ticker: str) -> Optional[dict]:
        """Detect RSI oversold (<35) or overbought (>65) conditions."""
        rsi = ta.momentum.RSIIndicator(close=df["Close"], window=14).rsi()
        if len(rsi.dropna()) < 5:
            return None
        current_rsi = float(rsi.iloc[-1])
        if current_rsi < 35:
            return {
                "pattern": "rsi_oversold",
                "direction": "bullish",
                "confidence": round(min(0.85, 0.4 + (35 - current_rsi) / 50), 2),
                "explanation": f"RSI at {current_rsi:.1f} — oversold territory (below 35). Potential bounce opportunity.",
                "current_rsi": current_rsi,
                "ticker": ticker,
            }
        if current_rsi > 65:
            return {
                "pattern": "rsi_overbought",
                "direction": "bearish",
                "confidence": round(min(0.85, 0.4 + (current_rsi - 65) / 50), 2),
                "explanation": f"RSI at {current_rsi:.1f} — overbought territory (above 65). Risk of pullback.",
                "current_rsi": current_rsi,
                "ticker": ticker,
            }
        return None

    def _detect_trend_strength(self, df: pd.DataFrame, ticker: str) -> Optional[dict]:
        """Detect strong trend using price vs SMA20/SMA50."""
        sma20 = ta.trend.SMAIndicator(close=df["Close"], window=20).sma_indicator()
        sma50 = ta.trend.SMAIndicator(close=df["Close"], window=50).sma_indicator()
        if len(sma50.dropna()) < 5:
            return None

        price = float(df["Close"].iloc[-1])
        s20 = float(sma20.iloc[-1])
        s50 = float(sma50.iloc[-1])

        if price < s20 < s50:
            pct_below = (s50 - price) / s50 * 100
            return {
                "pattern": "downtrend",
                "direction": "bearish",
                "confidence": round(min(0.8, 0.4 + pct_below / 20), 2),
                "explanation": f"Price ₹{price:.0f} below SMA20 (₹{s20:.0f}) and SMA50 (₹{s50:.0f}) — {pct_below:.1f}% below SMA50, bearish trend",
                "ticker": ticker,
            }
        if price > s20 > s50:
            pct_above = (price - s50) / s50 * 100
            return {
                "pattern": "uptrend",
                "direction": "bullish",
                "confidence": round(min(0.8, 0.4 + pct_above / 20), 2),
                "explanation": f"Price ₹{price:.0f} above SMA20 (₹{s20:.0f}) and SMA50 (₹{s50:.0f}) — {pct_above:.1f}% above SMA50, bullish trend",
                "ticker": ticker,
            }
        return None

    def _detect_golden_death_cross(self, df: pd.DataFrame, ticker: str) -> Optional[dict]:
        """Detect golden cross (50 SMA > 200 SMA) or death cross."""
        if len(df) < 200:
            return None

        sma50 = ta.trend.SMAIndicator(close=df["Close"], window=50).sma_indicator()
        sma200 = ta.trend.SMAIndicator(close=df["Close"], window=200).sma_indicator()

        if len(sma200.dropna()) < 5:
            return None

        # Check for crossover in last 5 days
        for i in range(-5, 0):
            prev_diff = sma50.iloc[i - 1] - sma200.iloc[i - 1]
            curr_diff = sma50.iloc[i] - sma200.iloc[i]

            if pd.isna(prev_diff) or pd.isna(curr_diff):
                continue

            if prev_diff < 0 and curr_diff > 0:
                return {
                    "pattern": "golden_cross",
                    "direction": "bullish",
                    "confidence": 0.75,
                    "explanation": f"50-day SMA (₹{sma50.iloc[-1]:.2f}) crossed above 200-day SMA (₹{sma200.iloc[-1]:.2f}) — Golden Cross, bullish long-term trend",
                    "ticker": ticker,
                }
            if prev_diff > 0 and curr_diff < 0:
                return {
                    "pattern": "death_cross",
                    "direction": "bearish",
                    "confidence": 0.75,
                    "explanation": f"50-day SMA (₹{sma50.iloc[-1]:.2f}) crossed below 200-day SMA (₹{sma200.iloc[-1]:.2f}) — Death Cross, bearish long-term trend",
                    "ticker": ticker,
                }
        return None
