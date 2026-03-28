"""
Market API router — radar, patterns, backtest, flows, portfolio, filings, OHLCV.
"""
import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class PortfolioInput(BaseModel):
    holdings: list[dict]  # [{ticker, quantity, buy_price}, ...]


@router.get("/radar")
async def get_radar(top_n: int = Query(10, le=50)):
    """Top N opportunity signals by Alpha Score."""
    from src.pipeline.fusion_engine import FusionEngine
    from src.data.ticker_universe import get_all_tickers

    tickers = get_all_tickers()
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
            return con.execute("""
                SELECT * FROM v_recent_news
                WHERE ? = ANY(tickers)
                ORDER BY published_at DESC LIMIT ?
            """, [ticker.upper(), limit]).fetchdf().to_dict(orient="records")
        return con.execute("SELECT * FROM v_recent_news LIMIT ?", [limit]).fetchdf().to_dict(orient="records")
    except Exception:
        return []
    finally:
        con.close()


@router.get("/tickers")
async def get_tickers(sector: str = Query("", description="Filter by sector")):
    """Get available tickers (dynamic from DuckDB, not hardcoded)."""
    from src.data.ticker_universe import get_all_tickers, get_tickers_by_sector, get_sectors
    if sector:
        return {"tickers": get_tickers_by_sector(sector)}
    return {"tickers": get_all_tickers(), "sectors": get_sectors()}


@router.get("/tickers/popular")
async def get_popular_tickers():
    """Get top tickers by market cap for quick-access buttons."""
    import duckdb
    from src.data.market_schema import get_db_path
    try:
        con = duckdb.connect(get_db_path(), read_only=True)
        rows = con.execute(
            "SELECT ticker FROM dim_stocks ORDER BY market_cap_cr DESC LIMIT 10"
        ).fetchall()
        con.close()
        tickers = [r[0] for r in rows]
        return {"tickers": tickers if tickers else ["RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN"]}
    except Exception:
        return {"tickers": ["RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN"]}


@router.get("/ohlcv/{ticker}")
async def get_ohlcv(ticker: str, period: str = Query("6mo"), indicators: bool = Query(False)):
    """OHLCV data for charting (consumed by TradingView Lightweight Charts).

    When indicators=True, returns extended format:
      { candles: [...], sma20: [...], sma50: [...], rsi: [...] }
    When indicators=False (default), returns flat candle list for backward compatibility.
    """
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

    if not indicators:
        return records

    # Compute technical indicators
    try:
        import pandas as pd
        from src.agents.technical_agent import TechnicalAgent

        ta_agent = TechnicalAgent()
        close = df["Close"]
        timestamps = [
            int(date.timestamp()) if hasattr(date, "timestamp") else int(pd.Timestamp(date).timestamp())
            for date in df.index
        ]

        rsi_series = ta_agent._calculate_rsi(close, window=14)
        sma20_series = ta_agent._calculate_sma(close, window=20)
        sma50_series = ta_agent._calculate_sma(close, window=50)

        def _to_time_value(series, ts_list):
            result = []
            for ts, (_, val) in zip(ts_list, series.items()):
                if pd.notna(val):
                    result.append({"time": ts, "value": round(float(val), 4)})
            return result

        return {
            "candles": records,
            "sma20": _to_time_value(sma20_series, timestamps),
            "sma50": _to_time_value(sma50_series, timestamps),
            "rsi": _to_time_value(rsi_series, timestamps),
        }
    except Exception:
        # Fallback: return candles only in extended format so frontend can detect it
        return {"candles": records, "sma20": [], "sma50": [], "rsi": []}


@router.get("/anomalies/{ticker}")
async def get_anomalies(ticker: str, period: str = Query("3mo", description="OHLCV history period")):
    """Detect price/volume anomalies using online ML (AnomalyAgent with River)."""
    try:
        from src.agents.anomaly_agent import get_anomaly_agent
        from src.connectors.nse_connector import get_nse_connector

        nse = get_nse_connector()

        # Get historical OHLCV data
        try:
            df = await asyncio.to_thread(nse.get_historical_data, ticker, period=period)
        except Exception as e:
            logger.debug(f"NSE OHLCV failed for {ticker}: {e}")
            # Try yfinance fallback
            import yfinance as yf
            hist = yf.Ticker(f"{ticker}.NS").history(period=period)
            df = hist

        if df is None or (hasattr(df, 'empty') and df.empty):
            return {"ticker": ticker, "anomalies": [], "fed_ticks": 0, "error": "No OHLCV data available"}

        agent = get_anomaly_agent()

        # Reset anomalies for fresh computation
        agent.clear_anomalies()

        # Feed historical ticks
        closes = df['Close'].tolist() if 'Close' in df.columns else []
        volumes = df['Volume'].tolist() if 'Volume' in df.columns else [0] * len(closes)

        fed = 0
        for i in range(1, len(closes)):
            try:
                close_val = float(closes[i])
                prev_close = float(closes[i - 1])
                vol_val = float(volumes[i]) if i < len(volumes) else 0
                change_pct = ((close_val - prev_close) / prev_close) * 100 if prev_close != 0 else 0

                agent.feed_price(ticker, close_val, int(vol_val), change_pct)
                fed += 1
            except Exception:
                continue

        anomalies = agent.get_recent_anomalies(limit=10)

        return {
            "ticker": ticker,
            "anomalies": anomalies,
            "fed_ticks": fed,
        }
    except Exception as e:
        logger.error(f"Anomaly detection failed for {ticker}: {e}")
        return {"ticker": ticker, "anomalies": [], "fed_ticks": 0, "error": str(e)}


@router.get("/screener")
async def get_screener(
    sector: str = Query("", description="Filter by sector"),
    direction: str = Query("", description="Filter by direction: bullish/bearish"),
    min_alpha: float = Query(0.0, description="Minimum alpha score (0-100)"),
    limit: int = Query(20, le=50, description="Max results"),
):
    """Top stock signals from v_stock_screener DuckDB view."""
    import duckdb
    from src.data.market_schema import get_db_path

    try:
        con = duckdb.connect(get_db_path(), read_only=True)
        try:
            sql = """
                SELECT * FROM v_stock_screener
                WHERE latest_alpha_score IS NOT NULL
            """
            params = []

            if sector:
                sql += " AND sector = ?"
                params.append(sector)
            if direction:
                sql += " AND latest_signal_dir = ?"
                params.append(direction.lower())
            if min_alpha > 0:
                sql += " AND latest_alpha_score >= ?"
                params.append(min_alpha)

            sql += " ORDER BY latest_alpha_score DESC NULLS LAST LIMIT ?"
            params.append(limit)

            df = con.execute(sql, params).fetchdf()

            sectors_df = con.execute(
                "SELECT DISTINCT sector FROM v_stock_screener WHERE sector IS NOT NULL ORDER BY sector"
            ).fetchdf()

            return {
                "stocks": df.to_dict(orient="records"),
                "sectors": sectors_df["sector"].tolist() if not sectors_df.empty else [],
                "total": len(df),
            }
        except Exception as e:
            logger.warning(f"Screener query failed: {e}")
            return {"stocks": [], "sectors": [], "total": 0, "error": str(e)}
        finally:
            con.close()
    except Exception as e:
        logger.error(f"Screener DB connection failed: {e}")
        return {"stocks": [], "sectors": [], "total": 0, "error": "Database unavailable"}


@router.get("/fundamentals/{ticker}")
async def get_fundamentals(ticker: str):
    """Get stock fundamentals from Groww API."""
    try:
        from src.connectors.groww_connector import get_groww_connector
        groww = get_groww_connector()

        fundamentals = {}
        quote = {}

        try:
            fundamentals = await asyncio.to_thread(groww.get_fundamentals, ticker) if hasattr(groww, 'get_fundamentals') else {}
        except Exception as e:
            logger.debug(f"Groww fundamentals failed: {e}")

        try:
            quote = await asyncio.to_thread(groww.get_stock_quote, ticker) if hasattr(groww, 'get_stock_quote') else {}
        except Exception as e:
            logger.debug(f"Groww quote failed: {e}")

        return {
            "ticker": ticker,
            "pe_ratio": fundamentals.get("pe_ratio"),
            "pb_ratio": fundamentals.get("pb_ratio"),
            "dividend_yield": fundamentals.get("dividend_yield"),
            "roe": fundamentals.get("roe"),
            "market_cap_cr": fundamentals.get("market_cap_cr"),
            "year_high": quote.get("year_high"),
            "year_low": quote.get("year_low"),
            "current_price": quote.get("price"),
            "source": "Groww",
        }
    except Exception as e:
        logger.warning(f"Fundamentals fetch failed for {ticker}: {e}")
        return {
            "ticker": ticker,
            "error": "Fundamentals data unavailable — configure GROWW_API_TOKEN in .env",
            "pe_ratio": None, "pb_ratio": None, "dividend_yield": None,
            "roe": None, "market_cap_cr": None, "year_high": None, "year_low": None,
            "current_price": None,
        }
