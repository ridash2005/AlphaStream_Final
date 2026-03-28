"""
Alpha Score Fusion Engine.

Combines signals from all agents into a single actionable score (0-100).
"""
import logging
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

WEIGHTS = {
    "filing": 0.25,
    "technical": 0.25,
    "insider_flow": 0.20,
    "sentiment": 0.15,
    "backtest": 0.15,
}

DIRECTION_THRESHOLDS = {
    "STRONG_BUY": 80,
    "BUY": 60,
    "HOLD": 40,
    "SELL": 20,
    "STRONG_SELL": 0,
}


def _normalize_score(raw: float, min_val: float = -1.0, max_val: float = 1.0) -> float:
    """Normalize a raw score to 0-100 range."""
    clamped = max(min_val, min(max_val, raw))
    return ((clamped - min_val) / (max_val - min_val)) * 100


def _get_direction(alpha_score: float) -> str:
    """Map alpha score to direction label."""
    if alpha_score >= 80:
        return "STRONG_BUY"
    elif alpha_score >= 60:
        return "BUY"
    elif alpha_score >= 40:
        return "HOLD"
    elif alpha_score >= 20:
        return "SELL"
    return "STRONG_SELL"


class FusionEngine:
    """Combines multi-agent signals into Alpha Score."""

    def compute_alpha_score(
        self,
        ticker: str,
        sentiment_data: dict = None,
        technical_data: dict = None,
        insider_data: dict = None,
        flow_data: dict = None,
        pattern_data: list = None,
        backtest_data: dict = None,
        filing_data: dict = None,
    ) -> dict[str, Any]:
        """Compute Alpha Score from all agent signals."""
        signals = []
        weighted_sum = 0.0
        total_weight = 0.0

        # Technical signal (0-100)
        tech_score = 50.0
        if technical_data:
            raw = technical_data.get("technical_score", 0)
            tech_score = _normalize_score(raw, -1.0, 1.0)
            signals.append({
                "type": "technical",
                "score": round(tech_score, 1),
                "detail": technical_data.get("signal", "HOLD"),
                "evidence": technical_data.get("key_signals", []),
            })
            weighted_sum += tech_score * WEIGHTS["technical"]
            total_weight += WEIGHTS["technical"]

        # Sentiment signal (0-100)
        sent_score = 50.0
        if sentiment_data:
            raw = sentiment_data.get("sentiment_score", 0)
            sent_score = _normalize_score(raw, -1.0, 1.0)
            signals.append({
                "type": "sentiment",
                "score": round(sent_score, 1),
                "detail": sentiment_data.get("sentiment_label", "NEUTRAL"),
                "evidence": sentiment_data.get("key_factors", []),
            })
            weighted_sum += sent_score * WEIGHTS["sentiment"]
            total_weight += WEIGHTS["sentiment"]

        # Insider + Flow signal (0-100)
        insider_flow_score = 50.0
        if insider_data:
            raw = insider_data.get("insider_score", 0)
            insider_flow_score = _normalize_score(raw, -1.0, 1.0)
            signals.append({
                "type": "insider",
                "score": round(insider_flow_score, 1),
                "detail": insider_data.get("sentiment", "NEUTRAL"),
                "evidence": insider_data.get("key_transactions", []),
            })
        if flow_data:
            flow_conf = flow_data.get("confidence", 50)
            flow_dir = flow_data.get("flow_signal", "neutral")
            if flow_dir == "bullish":
                insider_flow_score = (insider_flow_score + flow_conf) / 2
            elif flow_dir == "bearish":
                insider_flow_score = (insider_flow_score + (100 - flow_conf)) / 2
            signals.append({
                "type": "flow",
                "score": round(flow_conf, 1),
                "detail": flow_dir,
                "evidence": flow_data.get("observations", []),
            })
        weighted_sum += insider_flow_score * WEIGHTS["insider_flow"]
        total_weight += WEIGHTS["insider_flow"]

        # Filing signal (0-100)
        filing_score = 50.0
        if filing_data:
            impact_map = {
                "significant_positive": 90, "mild_positive": 70,
                "neutral": 50, "mild_negative": 30, "significant_negative": 10,
            }
            filing_score = impact_map.get(filing_data.get("market_impact", "neutral"), 50)
            signals.append({
                "type": "filing",
                "score": round(filing_score, 1),
                "detail": filing_data.get("filing_type", "routine"),
                "evidence": filing_data.get("key_facts", []),
            })
            weighted_sum += filing_score * WEIGHTS["filing"]
            total_weight += WEIGHTS["filing"]

        # Backtest confidence multiplier
        backtest_score = 50.0
        if backtest_data and backtest_data.get("results"):
            best_horizon = max(
                backtest_data["results"].values(),
                key=lambda x: x.get("win_rate", 0),
                default={},
            )
            win_rate = best_horizon.get("win_rate", 0.5)
            backtest_score = win_rate * 100
            signals.append({
                "type": "backtest",
                "score": round(backtest_score, 1),
                "detail": f"win_rate={win_rate:.0%}",
                "evidence": [f"{backtest_data.get('instances_found', 0)} historical instances"],
            })
            weighted_sum += backtest_score * WEIGHTS["backtest"]
            total_weight += WEIGHTS["backtest"]

        # Pattern bonus
        if pattern_data:
            for p in pattern_data[:3]:
                signals.append({
                    "type": "pattern",
                    "score": round(p.get("confidence", 0.5) * 100, 1),
                    "detail": p.get("pattern", "unknown"),
                    "evidence": [p.get("explanation", "")],
                })

        # Compute final alpha score
        alpha_score = (weighted_sum / total_weight) if total_weight > 0 else 50.0
        alpha_score = round(max(0, min(100, alpha_score)), 1)
        direction = _get_direction(alpha_score)

        # Sort signals by score descending, take top 3
        signals.sort(key=lambda s: s["score"], reverse=True)

        return {
            "signal_id": str(uuid.uuid4())[:8],
            "ticker": ticker,
            "alpha_score": alpha_score,
            "direction": direction,
            "top_signals": signals[:3],
            "all_signals": signals,
            "timestamp": datetime.now().isoformat(),
        }

    def scan_opportunities(
        self, tickers: list[str], top_n: int = 10
    ) -> list[dict[str, Any]]:
        """Scan multiple tickers and return top N by Alpha Score."""
        from src.agents.technical_agent import TechnicalAgent
        from src.agents.pattern_agent import PatternAgent

        tech_agent = TechnicalAgent()
        pattern_agent = PatternAgent()
        results = []

        for ticker in tickers:
            try:
                tech = tech_agent.analyze(ticker)
                patterns = pattern_agent.detect_all(ticker, period="3mo")

                score = self.compute_alpha_score(
                    ticker=ticker,
                    technical_data=tech,
                    pattern_data=patterns,
                )
                results.append(score)
            except Exception as e:
                logger.warning(f"Scan failed for {ticker}: {e}")
                continue

        results.sort(key=lambda r: r["alpha_score"], reverse=True)
        return results[:top_n]
