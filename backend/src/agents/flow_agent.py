"""
Flow Analyst Agent — FII/DII institutional flow analysis.

Detects: buying streaks, FII/DII divergence, bulk deal anomalies.
"""
import logging
from typing import Any

from src.connectors.fii_dii_connector import get_fii_dii_connector

logger = logging.getLogger(__name__)


class FlowAgent:
    """Analyzes FII/DII flow patterns for market signals."""

    def __init__(self):
        self.connector = get_fii_dii_connector()

    def analyze(self, days: int = 30) -> dict[str, Any]:
        """Analyze FII/DII flow patterns and return signal."""
        flows = self.connector.get_daily_flows(days)
        if not flows:
            result = self._neutral("No FII/DII flow data available")
            result["flows"] = []
            return result

        # Detect streaks
        fii_streak = self.connector.detect_streak(flows, entity="fii", threshold_days=5)
        dii_streak = self.connector.detect_streak(flows, entity="dii", threshold_days=5)

        # Detect divergence
        divergence = self.connector.detect_divergence(flows)

        # Compute signal
        observations = []
        direction = "neutral"
        confidence = 50.0

        if fii_streak["is_significant"]:
            if fii_streak["direction"] == "buy":
                direction = "bullish"
                confidence = min(90, 60 + fii_streak["streak_days"] * 5)
                observations.append(
                    f"FII net buying streak: {fii_streak['streak_days']} consecutive sessions "
                    f"(₹{abs(fii_streak['total_net_cr']):.0f} Cr total)"
                )
            else:
                direction = "bearish"
                confidence = min(90, 60 + fii_streak["streak_days"] * 5)
                observations.append(
                    f"FII net selling streak: {fii_streak['streak_days']} consecutive sessions "
                    f"(₹{abs(fii_streak['total_net_cr']):.0f} Cr total)"
                )

        if divergence["divergence"]:
            observations.append(divergence["detail"])
            confidence = min(95, confidence + 10)

        if dii_streak["is_significant"]:
            observations.append(
                f"DII {dii_streak['direction']} streak: {dii_streak['streak_days']} days "
                f"(₹{abs(dii_streak['total_net_cr']):.0f} Cr)"
            )

        if not observations:
            observations.append("No significant FII/DII flow patterns detected")

        return {
            "flow_signal": direction,
            "confidence": round(confidence, 1),
            "fii_streak": fii_streak,
            "dii_streak": dii_streak,
            "divergence": divergence,
            "observations": observations,
            "flows": flows,
        }

    def _neutral(self, reason: str) -> dict[str, Any]:
        return {
            "flow_signal": "neutral",
            "confidence": 50.0,
            "fii_streak": {"streak_days": 0, "direction": "none"},
            "dii_streak": {"streak_days": 0, "direction": "none"},
            "divergence": {"divergence": False},
            "observations": [reason],
        }
