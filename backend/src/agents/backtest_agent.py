"""
Backtest Agent — Historical signal validation.

For any ticker + pattern, downloads 5yr history, finds all past instances,
computes forward returns at +5d/+10d/+30d.
"""
import logging
from typing import Any

import numpy as np
import pandas as pd

from src.connectors.base_connector import ensure_ns_suffix
from src.agents.pattern_agent import PatternAgent

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


class BacktestAgent:
    """Backtests signal patterns against historical data."""

    def __init__(self):
        self.pattern_agent = PatternAgent()

    def backtest_signal(
        self, ticker: str, pattern: str, lookback_years: int = 5
    ) -> dict[str, Any]:
        """
        Find all historical instances of a pattern and compute forward returns.

        Returns: {ticker, pattern, instances_found, results: {5d, 10d, 30d}}
        """
        if not YFINANCE_AVAILABLE:
            return {"error": "yfinance not available"}

        try:
            tk = yf.Ticker(ensure_ns_suffix(ticker))
            df = tk.history(period=f"{lookback_years}y", interval="1d")
            if df.empty or len(df) < 60:
                return {"error": f"Insufficient data for {ticker}"}
        except Exception as e:
            return {"error": str(e)}

        # Find pattern instances by scanning with a rolling window
        instances = self._find_pattern_instances(df, pattern)

        if not instances:
            return {
                "ticker": ticker,
                "pattern": pattern,
                "lookback_years": lookback_years,
                "instances_found": 0,
                "results": {},
                "message": f"No {pattern} instances found in {lookback_years}yr history",
            }

        # Compute forward returns for each instance
        results = {}
        for horizon_days in [5, 10, 30]:
            returns = []
            for idx in instances:
                if idx + horizon_days < len(df):
                    entry_price = df["Close"].iloc[idx]
                    exit_price = df["Close"].iloc[idx + horizon_days]
                    if entry_price != 0:
                        ret = (exit_price - entry_price) / entry_price * 100
                        returns.append(float(ret))

            if returns:
                wins = [r for r in returns if r > 0]
                results[f"{horizon_days}d"] = {
                    "win_rate": round(len(wins) / len(returns), 2),
                    "avg_return": round(np.mean(returns), 2),
                    "max_return": round(max(returns), 2),
                    "max_drawdown": round(min(returns), 2),
                    "sharpe": round(float(np.mean(returns) / (np.std(returns) + 1e-8)) if len(returns) > 1 else 0.0, 2),
                    "samples": len(returns),
                }

        return {
            "ticker": ticker,
            "pattern": pattern,
            "lookback_years": lookback_years,
            "instances_found": len(instances),
            "results": results,
        }

    def _find_pattern_instances(self, df: pd.DataFrame, pattern: str) -> list[int]:
        """Find all indices where the pattern was detected historically."""
        try:
            import ta as ta_lib
        except ImportError:
            return []

        if len(df) < 50:
            return []

        instances = []
        close = df["Close"]

        if pattern == "rsi_divergence":
            rsi = ta_lib.momentum.RSIIndicator(close=close, window=14).rsi()
            # Scan for RSI oversold bounces (< 30 then rising)
            for i in range(44, len(df) - 1):
                if rsi.iloc[i] < 30 and rsi.iloc[i] > rsi.iloc[i - 1]:
                    instances.append(i)

        elif pattern == "macd_crossover":
            macd = ta_lib.trend.MACD(close=close)
            hist = macd.macd_diff()
            for i in range(1, len(hist)):
                if not pd.isna(hist.iloc[i - 1]) and not pd.isna(hist.iloc[i]):
                    if hist.iloc[i - 1] < 0 and hist.iloc[i] > 0:
                        instances.append(i)

        elif pattern == "bollinger_breakout":
            bb = ta_lib.volatility.BollingerBands(close=close, window=20, window_dev=2)
            upper = bb.bollinger_hband()
            for i in range(1, len(df)):
                if not pd.isna(upper.iloc[i]) and close.iloc[i] > upper.iloc[i] and close.iloc[i - 1] <= upper.iloc[i - 1]:
                    instances.append(i)

        elif pattern == "volume_breakout":
            if "Volume" in df.columns:
                for i in range(20, len(df)):
                    avg_vol = df["Volume"].iloc[i - 20:i].mean()
                    if avg_vol > 0 and df["Volume"].iloc[i] > 2 * avg_vol:
                        instances.append(i)

        elif pattern in ("golden_cross", "death_cross"):
            if len(df) >= 200:
                sma50 = ta_lib.trend.SMAIndicator(close=close, window=50).sma_indicator()
                sma200 = ta_lib.trend.SMAIndicator(close=close, window=200).sma_indicator()
                for i in range(1, len(df)):
                    if pd.isna(sma50.iloc[i]) or pd.isna(sma200.iloc[i]):
                        continue
                    prev = sma50.iloc[i - 1] - sma200.iloc[i - 1]
                    curr = sma50.iloc[i] - sma200.iloc[i]
                    if not pd.isna(prev):
                        if pattern == "golden_cross" and prev < 0 and curr > 0:
                            instances.append(i)
                        elif pattern == "death_cross" and prev > 0 and curr < 0:
                            instances.append(i)

        return instances
