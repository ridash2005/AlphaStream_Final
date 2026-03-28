"""
Market API router — radar, patterns, backtest, flows, portfolio, filings, OHLCV.
"""
import json
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


class PortfolioInput(BaseModel):
    holdings: list[dict]  # [{ticker, quantity, buy_price}, ...]


@router.get("/radar")
async def get_radar(top_n: int = Query(10, le=50)):
    """Top N opportunity signals by Alpha Score."""
    from src.pipeline.fusion_engine import FusionEngine
    import csv
    from pathlib import Path

    csv_path = Path(__file__).parents[2] / "data" / "nifty50_symbols.csv"
    tickers = []
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            tickers.append(row["ticker"])

    fe = FusionEngine()
    return fe.scan_opportunities(tickers[:20], top_n=top_n)


@router.get("/patterns/{ticker}")
async def get_patterns(ticker: str):
    """Detected chart patterns for a ticker."""
    from src.agents.pattern_agent import PatternAgent

    pa = PatternAgent()
    return pa.detect_all(ticker, period="6mo")


@router.get("/backtest/{ticker}/{pattern}")
async def get_backtest(ticker: str, pattern: str, years: int = Query(3, le=10)):
    """Historical backtest for a signal pattern on a ticker."""
    from src.agents.backtest_agent import BacktestAgent

    ba = BacktestAgent()
    return ba.backtest_signal(ticker, pattern, lookback_years=years)


@router.get("/flows")
async def get_flows(days: int = Query(30, le=90)):
    """FII/DII flow analysis."""
    from src.agents.flow_agent import FlowAgent

    fa = FlowAgent()
    return fa.analyze(days=days)


@router.post("/portfolio")
async def set_portfolio(body: PortfolioInput):
    """Set user portfolio for personalized analysis."""
    from src.pipeline.portfolio_manager import PortfolioManager

    pm = PortfolioManager()
    pm.set_holdings(body.holdings)
    return pm.get_portfolio_value()


@router.get("/portfolio/summary")
async def get_portfolio_summary():
    """Get portfolio summary with live P&L."""
    from src.pipeline.portfolio_manager import PortfolioManager
    pm = PortfolioManager()
    return pm.get_portfolio_value()


@router.get("/filings/{ticker}")
async def get_filings(ticker: str, days: int = Query(30, le=90)):
    """Get analyzed corporate filings for a ticker."""
    from src.connectors.bse_connector import get_bse_connector

    bse = get_bse_connector()
    return bse.get_announcements(days=days)


@router.get("/news")
async def get_news(ticker: str = Query(""), limit: int = Query(20, le=50)):
    """Get recent news, optionally filtered by ticker."""
    import duckdb
    from src.data.market_schema import get_db_path
    con = duckdb.connect(get_db_path(), read_only=True)
    try:
        if ticker:
            return con.execute(f"""
                SELECT * FROM v_recent_news
                WHERE '{ticker.upper()}' = ANY(tickers)
                ORDER BY published_at DESC LIMIT {limit}
            """).fetchdf().to_dict(orient="records")
        return con.execute(f"SELECT * FROM v_recent_news LIMIT {limit}").fetchdf().to_dict(orient="records")
    except Exception:
        return []
    finally:
        con.close()


@router.get("/ohlcv/{ticker}")
async def get_ohlcv(ticker: str, period: str = Query("6mo")):
    """OHLCV data for charting (consumed by TradingView Lightweight Charts)."""
    from src.connectors.nse_connector import get_nse_connector

    nse = get_nse_connector()
    df = nse.get_historical_data(ticker, period=period)
    if df.empty:
        return []

    records = []
    for date, row in df.iterrows():
        records.append({
            "time": int(date.timestamp()) if hasattr(date, "timestamp") else str(date),
            "open": round(float(row.get("Open", 0)), 2),
            "high": round(float(row.get("High", 0)), 2),
            "low": round(float(row.get("Low", 0)), 2),
            "close": round(float(row.get("Close", 0)), 2),
            "volume": int(row.get("Volume", 0)),
        })
    return records
