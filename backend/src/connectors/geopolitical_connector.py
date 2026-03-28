"""
Geopolitical Risk Connector — India-focused risk context.

Ported from WorldMonitor's country-instability.ts scoring model.
Provides a lightweight India risk score based on news classification
and static baseline risk.
"""

import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

SLOW_TTL = 1800  # 30 min
STALE_TTL = 3600  # 1 hr

# India configuration from WorldMonitor countries.ts
INDIA_CONFIG = {
    "code": "IN",
    "name": "India",
    "scoring_keywords": ["india", "delhi", "modi"],
    "search_aliases": ["india", "indian", "new delhi", "modi", "nse", "sensex", "nifty"],
    "baseline_risk": 20,  # 0-100, moderate baseline
    "event_multiplier": 0.8,
}

# Neighboring/relevant country baselines (affects India indirectly)
REGIONAL_BASELINES = {
    "PK": {"name": "Pakistan", "baseline": 35, "keywords": ["pakistan", "islamabad"]},
    "CN": {"name": "China", "baseline": 25, "keywords": ["china", "beijing", "pla"]},
    "LK": {"name": "Sri Lanka", "baseline": 20, "keywords": ["sri lanka", "colombo"]},
    "BD": {"name": "Bangladesh", "baseline": 20, "keywords": ["bangladesh", "dhaka"]},
    "MM": {"name": "Myanmar", "baseline": 40, "keywords": ["myanmar", "burma"]},
}

# Geopolitical hotspots affecting India (from WorldMonitor geo.ts)
INDIA_HOTSPOTS = [
    {
        "name": "Pakistan–Afghanistan Border",
        "keywords": ["pakistan", "afghanistan", "ttp", "taliban", "torkham", "waziristan"],
        "escalation_score": 4,
        "impact": "Defense stocks, INR volatility",
    },
    {
        "name": "India-China LAC",
        "keywords": ["galwan", "ladakh", "lac", "doklam", "arunachal"],
        "escalation_score": 3,
        "impact": "Defense stocks, IT sector (China ban risk)",
    },
    {
        "name": "Strait of Hormuz",
        "keywords": ["hormuz", "persian gulf", "iran", "houthi", "red sea"],
        "escalation_score": 4,
        "impact": "Oil imports, energy stocks, INR",
    },
    {
        "name": "Taiwan Strait",
        "keywords": ["taiwan", "taiwan strait", "south china sea"],
        "escalation_score": 3,
        "impact": "Semiconductor supply, IT/electronics sector",
    },
]


class _CacheEntry:
    __slots__ = ("data", "fetched_at")

    def __init__(self, data: Any, fetched_at: float):
        self.data = data
        self.fetched_at = fetched_at

    def is_fresh(self, ttl: float) -> bool:
        return (time.time() - self.fetched_at) < ttl

    def is_stale(self) -> bool:
        return (time.time() - self.fetched_at) >= STALE_TTL


class GeopoliticalConnector:
    """Computes India geopolitical risk score from news and static baselines."""

    _instance: Optional["GeopoliticalConnector"] = None

    def __init__(self):
        self._cache: dict[str, _CacheEntry] = {}
        self._recent_classifications: list[dict] = []

    @classmethod
    def get_instance(cls) -> "GeopoliticalConnector":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def ingest_classification(self, classification: dict, title: str = "") -> None:
        """Feed a news classification into the risk model."""
        self._recent_classifications.append({
            "classification": classification,
            "title": title,
            "timestamp": time.time(),
        })
        # Keep last 100 classifications, drop older than 24h
        cutoff = time.time() - 86400
        self._recent_classifications = [
            c for c in self._recent_classifications[-200:]
            if c["timestamp"] > cutoff
        ]
        # Invalidate cache
        self._cache.pop("india_risk", None)

    def get_india_risk(self) -> dict:
        """Compute India geopolitical risk score."""
        cached = self._cache.get("india_risk")
        if cached and cached.is_fresh(SLOW_TTL):
            return cached.data

        baseline = INDIA_CONFIG["baseline_risk"]
        multiplier = INDIA_CONFIG["event_multiplier"]

        # Score recent events
        event_boost = 0.0
        hotspot_alerts = []
        recent = [c for c in self._recent_classifications if time.time() - c["timestamp"] < 86400]

        for item in recent:
            cls = item["classification"]
            level = cls.get("level", "info")
            category = cls.get("category", "general")
            title_lower = item.get("title", "").lower()

            # Check if India-related
            india_related = any(kw in title_lower for kw in INDIA_CONFIG["scoring_keywords"])
            regional_related = any(
                any(kw in title_lower for kw in cfg["keywords"])
                for cfg in REGIONAL_BASELINES.values()
            )

            if not india_related and not regional_related:
                continue

            # Event score by level
            level_scores = {"critical": 15, "high": 8, "medium": 3, "low": 1, "info": 0}
            score = level_scores.get(level, 0) * multiplier

            # Boost for military/conflict affecting India
            if category in ("military", "conflict") and india_related:
                score *= 1.5

            event_boost += score

            # Check hotspot matches
            for hotspot in INDIA_HOTSPOTS:
                if any(kw in title_lower for kw in hotspot["keywords"]):
                    if hotspot["name"] not in [h["name"] for h in hotspot_alerts]:
                        hotspot_alerts.append({
                            "name": hotspot["name"],
                            "impact": hotspot["impact"],
                            "escalation": hotspot["escalation_score"],
                        })

        # Blend: 40% baseline + 60% events (capped)
        event_score = min(60, event_boost)
        blended = baseline * 0.4 + event_score * 0.6

        # Hotspot boost
        for alert in hotspot_alerts:
            blended += alert["escalation"] * 2

        final_score = min(100, max(0, blended))

        # Classify
        if final_score >= 60:
            level = "HIGH"
        elif final_score >= 40:
            level = "ELEVATED"
        elif final_score >= 20:
            level = "MODERATE"
        else:
            level = "LOW"

        result = {
            "score": round(final_score, 1),
            "level": level,
            "baseline": baseline,
            "event_boost": round(event_boost, 1),
            "recent_events": len(recent),
            "hotspot_alerts": hotspot_alerts,
            "summary": f"India geopolitical risk: {final_score:.0f}/100 ({level}). "
                       f"{len(hotspot_alerts)} active hotspot(s). "
                       f"{len(recent)} relevant events in 24h.",
        }

        self._cache["india_risk"] = _CacheEntry(result, time.time())
        return result


def get_geopolitical_connector() -> GeopoliticalConnector:
    """Get singleton instance."""
    return GeopoliticalConnector.get_instance()
