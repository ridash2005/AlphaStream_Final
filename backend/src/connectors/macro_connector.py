"""
Macro Economic Connector — FRED series + yield curve + macro signals.

Inspired by WorldMonitor's 10-factor composite scoring model.
Fetches key economic indicators that affect Indian market sentiment.
Uses FRED API key from .env (FRED_API_KEY).
"""

import logging
import time
from typing import Any, Optional

import httpx

from src.config import get_settings

logger = logging.getLogger(__name__)

SLOW_TTL = 1800   # 30 min
STALE_TTL = 3600  # 1 hr

# Key FRED series — based on WorldMonitor's seed-fear-greed.mjs
FRED_SERIES = {
    # Yield curve
    "T10Y2Y": "10Y-2Y Yield Spread",
    "DGS10": "10-Year Treasury Yield",
    "DGS2": "2-Year Treasury Yield",
    # Monetary policy
    "FEDFUNDS": "Federal Funds Rate",
    # Macro conditions
    "UNRATE": "Unemployment Rate",
    "CPIAUCSL": "CPI All Urban Consumers",
    # Dollar strength
    "DTWEXBGS": "Trade-Weighted USD Index (DXY proxy)",
    # Credit spreads (WorldMonitor uses these for Financial Stress Index)
    "BAMLH0A0HYM2": "HY OAS Spread",
    "BAMLC0A0CM": "IG OAS Spread",
    # Volatility (backup)
    "VIXCLS": "VIX Close",
}


class _CacheEntry:
    __slots__ = ("data", "fetched_at")

    def __init__(self, data: Any, fetched_at: float):
        self.data = data
        self.fetched_at = fetched_at

    def is_fresh(self, ttl: float) -> bool:
        return (time.time() - self.fetched_at) < ttl

    def is_stale(self) -> bool:
        return (time.time() - self.fetched_at) >= STALE_TTL


class MacroConnector:
    """Fetches macro economic signals from FRED API."""

    _instance: Optional["MacroConnector"] = None

    def __init__(self):
        self._cache: dict[str, _CacheEntry] = {}

    @classmethod
    def get_instance(cls) -> "MacroConnector":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_cached(self, key: str, ttl: float) -> Any | None:
        entry = self._cache.get(key)
        if entry and entry.is_fresh(ttl):
            return entry.data
        return None

    def _get_stale(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if entry and not entry.is_stale():
            return entry.data
        return None

    def _set_cache(self, key: str, data: Any) -> None:
        self._cache[key] = _CacheEntry(data, time.time())

    def _fetch_fred_latest(self, series_id: str) -> float | None:
        """Fetch latest observation from FRED."""
        cached = self._get_cached(f"fred_{series_id}", SLOW_TTL)
        if cached is not None:
            return cached

        settings = get_settings()
        api_key = settings.fred_api_key
        if not api_key:
            return None

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    "https://api.stlouisfed.org/fred/series/observations",
                    params={
                        "series_id": series_id,
                        "api_key": api_key,
                        "file_type": "json",
                        "sort_order": "desc",
                        "limit": 1,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                observations = data.get("observations", [])
                if observations:
                    val = observations[0].get("value", ".")
                    if val != ".":
                        result = float(val)
                        self._set_cache(f"fred_{series_id}", result)
                        return result
        except Exception as e:
            logger.debug(f"FRED {series_id} fetch failed: {e}")
        return None

    def get_yield_curve(self) -> dict:
        """Yield curve status: 2Y-10Y spread."""
        cached = self._get_cached("yield_curve", SLOW_TTL)
        if cached:
            return cached

        spread = self._fetch_fred_latest("T10Y2Y")

        if spread is not None:
            # Fixed thresholds: < 0 is inverted, 0 to 0.5 is flat, > 0.5 is normal
            if spread < 0:
                status = "INVERTED"
            elif spread < 0.5:
                status = "FLAT"
            else:
                status = "NORMAL"
            result = {"spread": round(spread, 3), "status": status}
        else:
            y10 = self._fetch_fred_latest("DGS10")
            y2 = self._fetch_fred_latest("DGS2")
            if y10 is not None and y2 is not None:
                spread = y10 - y2
                status = "INVERTED" if spread < 0 else "FLAT" if spread < 0.5 else "NORMAL"
                result = {"spread": round(spread, 3), "status": status, "y10": y10, "y2": y2}
            else:
                stale = self._get_stale("yield_curve")
                return stale or {"spread": None, "status": "UNKNOWN"}

        self._set_cache("yield_curve", result)
        return result

    def get_credit_spreads(self) -> dict:
        """HY and IG credit spreads — stress indicators."""
        cached = self._get_cached("credit_spreads", SLOW_TTL)
        if cached:
            return cached

        hy_spread = self._fetch_fred_latest("BAMLH0A0HYM2")
        ig_spread = self._fetch_fred_latest("BAMLC0A0CM")

        # HY spread: < 3% = low stress, 3-5% = moderate, > 5% = high stress
        hy_status = "UNKNOWN"
        if hy_spread is not None:
            if hy_spread < 3.0:
                hy_status = "LOW_STRESS"
            elif hy_spread < 5.0:
                hy_status = "MODERATE"
            else:
                hy_status = "HIGH_STRESS"

        result = {
            "hy_spread": round(hy_spread, 3) if hy_spread else None,
            "ig_spread": round(ig_spread, 3) if ig_spread else None,
            "hy_status": hy_status,
        }
        self._set_cache("credit_spreads", result)
        return result

    def get_macro_signals(self) -> dict:
        """Composite macro signals for market regime detection."""
        cached = self._get_cached("macro_signals", SLOW_TTL)
        if cached:
            return cached

        from src.connectors.global_market_connector import get_global_market_connector
        gmc = get_global_market_connector()

        vix_data = gmc.get_vix()
        fg_data = gmc.get_fear_greed()
        yield_data = self.get_yield_curve()
        credit_data = self.get_credit_spreads()
        commodities = gmc.get_commodity_quotes()
        currencies = gmc.get_currency_quotes()

        crude_change = next((c["change"] for c in commodities if c["symbol"] == "CL=F"), 0)
        gold_change = next((c["change"] for c in commodities if c["symbol"] == "GC=F"), 0)
        dxy_change = next((c["change"] for c in currencies if c["symbol"] == "DX-Y.NYB"), 0)

        # Fetch FRED macro indicators
        unemployment = self._fetch_fred_latest("UNRATE")
        fed_rate = self._fetch_fred_latest("FEDFUNDS")

        signals = []

        # 1. VIX
        vix_val = vix_data.get("value")
        vix_status = vix_data.get("status", "UNKNOWN")
        signals.append({
            "name": "VIX",
            "value": vix_val,
            "status": "BULLISH" if vix_status == "LOW" else "BEARISH" if vix_status in ("HIGH", "EXTREME") else "NEUTRAL",
            "description": f"VIX at {vix_val} ({vix_status})",
        })

        # 2. Fear & Greed
        fg_score = fg_data.get("score", 50)
        signals.append({
            "name": "Fear & Greed",
            "value": fg_score,
            "status": "BULLISH" if fg_score > 55 else "BEARISH" if fg_score < 45 else "NEUTRAL",
            "description": f"{fg_score:.0f} ({fg_data.get('label', 'Neutral')})",
        })

        # 3. Yield Curve
        yc_status = yield_data.get("status", "UNKNOWN")
        signals.append({
            "name": "Yield Curve",
            "value": yield_data.get("spread"),
            "status": "BEARISH" if yc_status == "INVERTED" else "BULLISH" if yc_status == "NORMAL" else "NEUTRAL",
            "description": f"2s10s: {yield_data.get('spread', '?')}% ({yc_status})",
        })

        # 4. Credit Spreads (HY OAS)
        hy_spread = credit_data.get("hy_spread")
        hy_status = credit_data.get("hy_status", "UNKNOWN")
        if hy_spread is not None:
            signals.append({
                "name": "HY Credit",
                "value": hy_spread,
                "status": "BULLISH" if hy_status == "LOW_STRESS" else "BEARISH" if hy_status == "HIGH_STRESS" else "NEUTRAL",
                "description": f"HY OAS: {hy_spread:.1f}% ({hy_status.replace('_', ' ').title()})",
            })

        # 5. Crude Oil (high oil = bearish for India — net importer)
        signals.append({
            "name": "Crude Oil",
            "value": crude_change,
            "status": "BEARISH" if crude_change > 3 else "BULLISH" if crude_change < -1 else "NEUTRAL",
            "description": f"WTI {crude_change:+.1f}% (high oil bearish for India)",
        })

        # 6. Gold (flight to safety)
        signals.append({
            "name": "Gold",
            "value": gold_change,
            "status": "BEARISH" if gold_change > 2 else "BULLISH" if gold_change < -1 else "NEUTRAL",
            "description": f"Gold {gold_change:+.1f}% (flight to safety signal)",
        })

        # 7. DXY (strong dollar = bearish for EM)
        signals.append({
            "name": "US Dollar",
            "value": dxy_change,
            "status": "BEARISH" if dxy_change > 0.5 else "BULLISH" if dxy_change < -0.3 else "NEUTRAL",
            "description": f"DXY {dxy_change:+.1f}% (strong USD bearish for EM)",
        })

        # 8. Unemployment
        if unemployment is not None:
            signals.append({
                "name": "US Unemployment",
                "value": unemployment,
                "status": "BULLISH" if unemployment < 4.0 else "BEARISH" if unemployment > 5.5 else "NEUTRAL",
                "description": f"US unemployment: {unemployment:.1f}%",
            })

        # 9. Fed Funds Rate
        if fed_rate is not None:
            signals.append({
                "name": "Fed Funds Rate",
                "value": fed_rate,
                "status": "BEARISH" if fed_rate > 5.0 else "BULLISH" if fed_rate < 3.0 else "NEUTRAL",
                "description": f"Fed rate: {fed_rate:.2f}%",
            })

        # Overall verdict
        bullish = sum(1 for s in signals if s["status"] == "BULLISH")
        bearish = sum(1 for s in signals if s["status"] == "BEARISH")
        total = len(signals)

        if bullish > bearish and bullish >= total // 2:
            verdict = "RISK-ON"
        elif bearish > bullish and bearish >= total // 2:
            verdict = "RISK-OFF"
        else:
            verdict = "MIXED"

        result = {
            "verdict": verdict,
            "bullish_count": bullish,
            "bearish_count": bearish,
            "total_signals": total,
            "signals": signals,
            "vix": vix_val,
            "yield_curve": yc_status,
            "fear_greed": fg_score,
        }

        self._set_cache("macro_signals", result)
        return result


def get_macro_connector() -> MacroConnector:
    """Get singleton instance."""
    return MacroConnector.get_instance()
