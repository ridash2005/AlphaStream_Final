"""
Global Market Router — WorldMonitor-sourced global intelligence.

Provides endpoints for global indices, commodities, VIX, Fear & Greed,
sector performance, and macro signals.
"""

from fastapi import APIRouter

from src.connectors.global_market_connector import get_global_market_connector
from src.connectors.macro_connector import get_macro_connector
from src.connectors.geopolitical_connector import get_geopolitical_connector

router = APIRouter()


@router.get("/indices")
async def get_global_indices():
    """Global stock indices (S&P 500, DOW, NASDAQ, NIFTY, SENSEX, etc.)."""
    gmc = get_global_market_connector()
    return {"data": gmc.get_global_indices()}


@router.get("/commodities")
async def get_commodity_quotes():
    """Commodity futures (Gold, Oil, Silver, Copper, etc.)."""
    gmc = get_global_market_connector()
    return {"data": gmc.get_commodity_quotes()}


@router.get("/crypto")
async def get_crypto_quotes():
    """Crypto quotes (BTC, ETH)."""
    gmc = get_global_market_connector()
    return {"data": gmc.get_crypto_quotes()}


@router.get("/vix")
async def get_vix():
    """VIX volatility index + status."""
    gmc = get_global_market_connector()
    return gmc.get_vix()


@router.get("/fear-greed")
async def get_fear_greed():
    """CNN Fear & Greed Index (0-100)."""
    gmc = get_global_market_connector()
    return gmc.get_fear_greed()


@router.get("/sectors")
async def get_sector_performance():
    """US sector ETF performance."""
    gmc = get_global_market_connector()
    return {"data": gmc.get_sector_performance()}


@router.get("/macro")
async def get_macro_signals():
    """Macro economic signals composite."""
    mc = get_macro_connector()
    return mc.get_macro_signals()


@router.get("/currencies")
async def get_currency_quotes():
    """INR/USD and DXY quotes."""
    gmc = get_global_market_connector()
    return {"data": gmc.get_currency_quotes()}


@router.get("/context")
async def get_global_context():
    """Combined global context blob (used by Decision Agent + frontend)."""
    gmc = get_global_market_connector()
    mc = get_macro_connector()
    ctx = gmc.get_decision_context()
    macro = mc.get_macro_signals()
    ctx["macro_verdict"] = macro.get("verdict", "MIXED")
    ctx["macro_signals"] = macro.get("signals", [])
    ctx["yield_curve"] = macro.get("yield_curve", "UNKNOWN")
    return ctx


@router.get("/geo-risk")
async def get_geopolitical_risk():
    """India geopolitical risk score (0-100) with hotspot alerts."""
    geo = get_geopolitical_connector()
    return geo.get_india_risk()


@router.post("/refresh")
async def refresh_global_data():
    """Force re-fetch all global market data."""
    gmc = get_global_market_connector()
    gmc.bootstrap()
    mc = get_macro_connector()
    mc.get_macro_signals()  # warm macro cache too
    return {"status": "refreshed"}
