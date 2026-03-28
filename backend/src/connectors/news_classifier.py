"""
News Threat Classifier — ported from WorldMonitor's _classifier.ts.

Keyword-based classification of news articles by threat level and category.
Used to score articles in the RAG pipeline and weight sentiment analysis.
"""

import re
from typing import Literal

ThreatLevel = Literal["critical", "high", "medium", "low", "info"]
EventCategory = Literal[
    "conflict", "protest", "disaster", "diplomatic", "economic",
    "terrorism", "cyber", "health", "environmental", "military",
    "crime", "infrastructure", "tech", "general",
]

# ── Keyword → (category, level, confidence) ────────────────────────

CRITICAL_KEYWORDS: dict[str, EventCategory] = {
    "nuclear strike": "military", "nuclear attack": "military",
    "nuclear war": "military", "invasion": "conflict",
    "declaration of war": "conflict", "martial law": "military",
    "coup": "military", "coup attempt": "military",
    "genocide": "conflict", "ethnic cleansing": "conflict",
    "chemical attack": "terrorism", "biological attack": "terrorism",
    "dirty bomb": "terrorism", "mass casualty": "conflict",
    "pandemic declared": "health", "health emergency": "health",
    "nato article 5": "military", "evacuation order": "disaster",
    "meltdown": "disaster", "nuclear meltdown": "disaster",
}

HIGH_KEYWORDS: dict[str, EventCategory] = {
    "war": "conflict", "armed conflict": "conflict",
    "airstrike": "conflict", "air strike": "conflict",
    "drone strike": "conflict", "missile": "military",
    "missile launch": "military", "troops deployed": "military",
    "military escalation": "military", "bombing": "conflict",
    "casualties": "conflict", "hostage": "terrorism",
    "terrorist": "terrorism", "terror attack": "terrorism",
    "assassination": "crime", "cyber attack": "cyber",
    "ransomware": "cyber", "data breach": "cyber",
    "sanctions": "economic", "embargo": "economic",
    "earthquake": "disaster", "tsunami": "disaster",
    "hurricane": "disaster", "typhoon": "disaster",
}

MEDIUM_KEYWORDS: dict[str, EventCategory] = {
    "protest": "protest", "protests": "protest",
    "riot": "protest", "riots": "protest",
    "unrest": "protest", "demonstration": "protest",
    "strike action": "protest", "military exercise": "military",
    "naval exercise": "military", "arms deal": "military",
    "diplomatic crisis": "diplomatic", "ambassador recalled": "diplomatic",
    "expel diplomats": "diplomatic", "trade war": "economic",
    "tariff": "economic", "recession": "economic",
    "inflation": "economic", "market crash": "economic",
    "flood": "disaster", "flooding": "disaster",
    "wildfire": "disaster", "volcano": "disaster",
    "eruption": "disaster", "outbreak": "health",
    "epidemic": "health", "oil spill": "environmental",
    "pipeline explosion": "infrastructure", "blackout": "infrastructure",
    "power outage": "infrastructure", "internet outage": "infrastructure",
    "derailment": "infrastructure",
}

LOW_KEYWORDS: dict[str, EventCategory] = {
    "election": "diplomatic", "referendum": "diplomatic",
    "summit": "diplomatic", "treaty": "diplomatic",
    "negotiation": "diplomatic", "ceasefire": "diplomatic",
    "climate change": "environmental", "pollution": "environmental",
    "drought": "environmental", "vaccine": "health",
    "disease": "health", "virus": "health",
    "interest rate": "economic", "gdp": "economic",
    "unemployment": "economic", "regulation": "economic",
}

# India-specific market keywords (finance variant extension)
INDIA_MARKET_KEYWORDS: dict[str, tuple[ThreatLevel, EventCategory]] = {
    "rbi rate": ("medium", "economic"),
    "repo rate": ("medium", "economic"),
    "sebi": ("low", "economic"),
    "sensex crash": ("high", "economic"),
    "nifty crash": ("high", "economic"),
    "rupee fall": ("medium", "economic"),
    "rupee depreciation": ("medium", "economic"),
    "fii outflow": ("medium", "economic"),
    "fii pullout": ("high", "economic"),
    "adani": ("low", "economic"),
    "modi policy": ("low", "diplomatic"),
    "kashmir": ("medium", "conflict"),
    "border tension": ("medium", "military"),
    "india pakistan": ("medium", "military"),
    "monsoon": ("low", "environmental"),
    "cyclone": ("medium", "disaster"),
}

# Exclusion keywords — noise filter
EXCLUSIONS = {
    "protein", "couples", "relationship", "dating", "diet", "fitness",
    "recipe", "cooking", "shopping", "fashion", "celebrity", "movie",
    "tv show", "sports", "game", "concert", "wedding", "vacation",
    "travel tips", "self-care", "wellness",
}

# Short keywords that need word boundary matching
SHORT_KEYWORDS = {
    "war", "coup", "ban", "vote", "riot", "riots", "hack",
    "talks", "ipo", "gdp", "virus", "disease", "flood",
}


def classify_article(title: str, content: str = "") -> dict:
    """
    Classify a news article by threat level and category.

    Returns:
        {
            "level": "critical"|"high"|"medium"|"low"|"info",
            "category": EventCategory,
            "confidence": 0.0-1.0,
            "matched_keyword": str | None,
        }
    """
    text = f"{title} {content}".lower()

    # 1. Exclusion check
    for excl in EXCLUSIONS:
        if excl in text:
            return {"level": "info", "category": "general", "confidence": 0.3, "matched_keyword": None}

    # 2. India-specific market keywords
    for kw, (level, category) in INDIA_MARKET_KEYWORDS.items():
        if kw in text:
            conf = {"critical": 0.9, "high": 0.8, "medium": 0.7, "low": 0.6}.get(level, 0.5)
            return {"level": level, "category": category, "confidence": conf, "matched_keyword": kw}

    # 3. Critical
    for kw, cat in CRITICAL_KEYWORDS.items():
        if _keyword_match(kw, text):
            return {"level": "critical", "category": cat, "confidence": 0.9, "matched_keyword": kw}

    # 4. High
    for kw, cat in HIGH_KEYWORDS.items():
        if _keyword_match(kw, text):
            return {"level": "high", "category": cat, "confidence": 0.8, "matched_keyword": kw}

    # 5. Medium
    for kw, cat in MEDIUM_KEYWORDS.items():
        if _keyword_match(kw, text):
            return {"level": "medium", "category": cat, "confidence": 0.7, "matched_keyword": kw}

    # 6. Low
    for kw, cat in LOW_KEYWORDS.items():
        if _keyword_match(kw, text):
            return {"level": "low", "category": cat, "confidence": 0.6, "matched_keyword": kw}

    # 7. Default
    return {"level": "info", "category": "general", "confidence": 0.3, "matched_keyword": None}


def _keyword_match(keyword: str, text: str) -> bool:
    """Match keyword in text, using word boundaries for short keywords."""
    if keyword in SHORT_KEYWORDS:
        return bool(re.search(rf"\b{re.escape(keyword)}\b", text))
    return keyword in text


def get_market_impact_score(classification: dict) -> float:
    """
    Convert threat classification to a market impact score (-1.0 to +1.0).
    Negative = bearish impact, positive = generally neutral/bullish.

    Used to weight sentiment analysis in the pipeline.
    """
    level = classification.get("level", "info")
    category = classification.get("category", "general")

    # Base impact by threat level
    base = {
        "critical": -0.8,
        "high": -0.5,
        "medium": -0.2,
        "low": 0.0,
        "info": 0.0,
    }.get(level, 0.0)

    # Category modifiers for Indian market context
    if category == "economic":
        base *= 1.2  # Economic news is most directly impactful
    elif category == "military" and level in ("critical", "high"):
        base *= 1.5  # Military escalation heavily affects EM markets
    elif category in ("diplomatic", "health"):
        base *= 0.8  # Less direct market impact

    return max(-1.0, min(1.0, base))
