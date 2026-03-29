"""
Global Market Router — WorldMonitor-sourced global intelligence.

Provides endpoints for global indices, commodities, VIX, Fear & Greed,
sector performance, and macro signals.
"""

import asyncio
import logging

from fastapi import APIRouter

from src.connectors.global_market_connector import get_global_market_connector
from src.connectors.macro_connector import get_macro_connector
from src.connectors.geopolitical_connector import get_geopolitical_connector

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/indices")
async def get_global_indices():
    """Global stock indices (S&P 500, DOW, NASDAQ, NIFTY, SENSEX, etc.)."""
    try:
        gmc = get_global_market_connector()
        return {"data": gmc.get_global_indices()}
    except Exception as e:
        logger.error(f"Global indices fetch failed: {e}")
        return {"data": []}


@router.get("/commodities")
async def get_commodity_quotes():
    """Commodity futures (Gold, Oil, Silver, Copper, etc.)."""
    try:
        gmc = get_global_market_connector()
        return {"data": gmc.get_commodity_quotes()}
    except Exception as e:
        logger.error(f"Commodity quotes fetch failed: {e}")
        return {"data": []}


@router.get("/crypto")
async def get_crypto_quotes():
    """Crypto quotes (BTC, ETH)."""
    try:
        gmc = get_global_market_connector()
        return {"data": gmc.get_crypto_quotes()}
    except Exception as e:
        logger.error(f"Crypto quotes fetch failed: {e}")
        return {"data": []}


@router.get("/vix")
async def get_vix():
    """VIX volatility index + status."""
    try:
        gmc = get_global_market_connector()
        return {"data": gmc.get_vix()}
    except Exception as e:
        logger.error(f"VIX fetch failed: {e}")
        return {"data": {"value": None, "change": 0, "status": "UNKNOWN"}}


@router.get("/fear-greed")
async def get_fear_greed():
    """CNN Fear & Greed Index (0-100)."""
    try:
        gmc = get_global_market_connector()
        return {"data": gmc.get_fear_greed()}
    except Exception as e:
        logger.error(f"Fear & Greed fetch failed: {e}")
        return {"data": {"score": 50, "label": "Neutral", "previous": 50}}


@router.get("/sectors")
async def get_sector_performance():
    """US sector ETF performance."""
    try:
        gmc = get_global_market_connector()
        return {"data": gmc.get_sector_performance()}
    except Exception as e:
        logger.error(f"Sector performance fetch failed: {e}")
        return {"data": []}


@router.get("/macro")
async def get_macro_signals():
    """Macro economic signals composite."""
    try:
        mc = get_macro_connector()
        return {"data": mc.get_macro_signals()}
    except Exception as e:
        logger.error(f"Macro signals fetch failed: {e}")
        return {"data": {"verdict": "MIXED", "bullish_count": 0, "bearish_count": 0, "total_signals": 0, "signals": []}}


@router.get("/currencies")
async def get_currency_quotes():
    """INR/USD and DXY quotes."""
    try:
        gmc = get_global_market_connector()
        return {"data": gmc.get_currency_quotes()}
    except Exception as e:
        logger.error(f"Currency quotes fetch failed: {e}")
        return {"data": []}


@router.get("/context")
async def get_global_context():
    """Combined global context blob (used by Decision Agent + frontend)."""
    try:
        gmc = get_global_market_connector()
        mc = get_macro_connector()
        ctx = gmc.get_decision_context() or {}
        macro = mc.get_macro_signals() or {}
        ctx["macro_verdict"] = macro.get("verdict", "MIXED")
        ctx["macro_signals"] = macro.get("signals", [])
        ctx["yield_curve"] = macro.get("yield_curve", "UNKNOWN")
        return {"data": ctx}
    except Exception as e:
        logger.error(f"Global context fetch failed: {e}")
        return {"data": {}}


@router.get("/geo-risk")
async def get_geopolitical_risk():
    """India geopolitical risk score (0-100) with hotspot alerts."""
    try:
        geo = get_geopolitical_connector()
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, geo.get_india_risk)
        return {"data": result}
    except Exception as e:
        logger.error(f"Geo-risk fetch failed: {e}")
        return {"data": {"score": 0, "level": "UNKNOWN", "hotspot_alerts": [], "recent_events": 0, "summary": str(e)}}


@router.post("/refresh")
async def refresh_global_data():
    """Force re-fetch all global market data."""
    try:
        gmc = get_global_market_connector()
        gmc.bootstrap()
        mc = get_macro_connector()
        mc.get_macro_signals()  # warm macro cache too
        return {"status": "refreshed"}
    except Exception as e:
        logger.error(f"Global data refresh failed: {e}")
        return {"status": "error", "detail": str(e)}
