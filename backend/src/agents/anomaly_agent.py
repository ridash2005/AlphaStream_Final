"""
Anomaly Detection Agent — Online ML with River.

Learns incrementally from each price tick (no batch retraining).
Detects: price anomalies, volume spikes, sentiment drift.
"""
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    from river import anomaly, drift, stats
    RIVER_AVAILABLE = True
except ImportError:
    RIVER_AVAILABLE = False
    logger.warning("river not installed — anomaly detection disabled")


class AnomalyAgent:
    """Online anomaly detection using River incremental ML."""

    def __init__(self):
        if not RIVER_AVAILABLE:
            self._models = {}
            return

        self._price_models: dict[str, anomaly.HalfSpaceTrees] = {}
        self._volume_mean: dict[str, stats.Mean] = {}
        self._volume_var: dict[str, stats.Var] = {}
        self._sentiment_drift: dict[str, drift.ADWIN] = {}
        self._tick_count: dict[str, int] = {}
        self._anomalies: list[dict] = []

    def _get_price_model(self, ticker: str) -> "anomaly.HalfSpaceTrees":
        if ticker not in self._price_models:
            self._price_models[ticker] = anomaly.HalfSpaceTrees(
                n_trees=10, height=6, window_size=50, seed=42
            )
        return self._price_models[ticker]

    def _get_volume_stats(self, ticker: str):
        if ticker not in self._volume_mean:
            self._volume_mean[ticker] = stats.Mean()
            self._volume_var[ticker] = stats.Var()
            self._tick_count[ticker] = 0
        return self._volume_mean[ticker], self._volume_var[ticker]

    def feed_price(self, ticker: str, price: float, volume: int,
                   change_pct: float = 0) -> Optional[dict]:
        """Feed a price tick. Returns anomaly dict if detected, else None."""
        if not RIVER_AVAILABLE:
            return None

        # Price anomaly (Half-Space Trees)
        model = self._get_price_model(ticker)
        features = {"price": price, "volume": float(volume), "change": change_pct}
        score = model.score_one(features)
        model.learn_one(features)

        # Volume anomaly (z-score)
        vol_mean, vol_var = self._get_volume_stats(ticker)
        vol_mean.update(float(volume))
        vol_var.update(float(volume))
        self._tick_count[ticker] = self._tick_count.get(ticker, 0) + 1
        vol_std = vol_var.get() ** 0.5 if vol_var.get() > 0 else 1
        vol_z = (float(volume) - vol_mean.get()) / vol_std if vol_std > 0 and self._tick_count[ticker] > 5 else 0

        anomaly_detected = None

        if score > 0.7:  # High anomaly score
            anomaly_detected = {
                "ticker": ticker,
                "type": "price_anomaly",
                "score": round(score, 3),
                "detail": f"Unusual price movement detected (anomaly score {score:.2f}). "
                          f"Price: ₹{price:.2f}, Change: {change_pct:+.2f}%",
                "direction": "bearish" if change_pct < -2 else "bullish" if change_pct > 2 else "neutral",
            }

        if abs(vol_z) > 2.5:  # Volume z-score > 2.5
            anomaly_detected = {
                "ticker": ticker,
                "type": "volume_anomaly",
                "score": round(abs(vol_z) / 5, 3),
                "detail": f"Volume spike: {volume:,} ({vol_z:.1f} std deviations from mean). "
                          f"Price: ₹{price:.2f}",
                "direction": "bullish" if change_pct > 0 else "bearish",
            }

        if anomaly_detected:
            self._anomalies.append(anomaly_detected)

        return anomaly_detected

    def feed_sentiment(self, ticker: str, sentiment_score: float) -> Optional[dict]:
        """Feed a sentiment score. Returns drift alert if detected."""
        if not RIVER_AVAILABLE:
            return None

        if ticker not in self._sentiment_drift:
            self._sentiment_drift[ticker] = drift.ADWIN()

        detector = self._sentiment_drift[ticker]
        # Normalize sentiment to 0-1 for ADWIN
        normalized = (sentiment_score + 1) / 2
        detector.update(normalized)

        if detector.drift_detected:
            return {
                "ticker": ticker,
                "type": "sentiment_drift",
                "score": 0.8,
                "detail": f"Sentiment shift detected for {ticker}. "
                          f"Current sentiment: {sentiment_score:.2f}",
                "direction": "bearish" if sentiment_score < 0 else "bullish",
            }
        return None

    def get_recent_anomalies(self, limit: int = 10) -> list[dict]:
        """Get most recent anomalies."""
        return self._anomalies[-limit:]

    def clear_anomalies(self):
        self._anomalies.clear()


_anomaly_agent = None


def get_anomaly_agent() -> AnomalyAgent:
    global _anomaly_agent
    if _anomaly_agent is None:
        _anomaly_agent = AnomalyAgent()
    return _anomaly_agent
