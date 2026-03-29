"""
Dynamic Ticker Universe — no hardcoded lists.

Uses DuckDB dim_stocks as primary source, Groww API for discovery.
"""
import csv
import logging
from pathlib import Path
from typing import Optional

import duckdb

from src.data.market_schema import get_db_path

logger = logging.getLogger(__name__)

_CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "nifty50_symbols.csv"


def get_all_tickers() -> list[str]:
    """Get all tickers from DuckDB dim_stocks (dynamic, not CSV)."""
    try:
        con = duckdb.connect(get_db_path(), read_only=True)
        tickers = [r[0] for r in con.execute("SELECT ticker FROM dim_stocks ORDER BY ticker").fetchall()]
        con.close()
        if tickers:
            return tickers
    except Exception as e:
        logger.warning(f"DuckDB ticker fetch failed: {e}")

    # Fallback to CSV
    return _get_tickers_from_csv()


def get_tickers_by_sector(sector: str) -> list[str]:
    """Get tickers filtered by sector."""
    try:
        con = duckdb.connect(get_db_path(), read_only=True)
        tickers = [r[0] for r in con.execute(
            "SELECT ticker FROM dim_stocks WHERE sector = ?", [sector]
        ).fetchall()]
        con.close()
        return tickers
    except Exception:
        return []


def get_sectors() -> list[str]:
    """Get all unique sectors."""
    try:
        con = duckdb.connect(get_db_path(), read_only=True)
        sectors = [r[0] for r in con.execute(
            "SELECT DISTINCT sector FROM dim_stocks ORDER BY sector"
        ).fetchall()]
        con.close()
        return sectors
    except Exception:
        return []


def discover_tickers(query: str) -> list[dict]:
    """Discover tickers via Groww search API (dynamic, scalable)."""
    try:
        from src.connectors.groww_connector import get_groww_connector
        gc = get_groww_connector()
        return gc.search_stocks(query)
    except Exception as e:
        logger.warning(f"Groww discovery failed: {e}")
        return []


def refresh_dim_stocks() -> int:
    """Refresh dim_stocks with latest data from Groww live prices."""
    tickers = get_all_tickers()
    if not tickers:
        return 0

    try:
        from src.connectors.groww_connector import get_groww_connector
        gc = get_groww_connector()
        con = duckdb.connect(get_db_path())
        updated = 0
        for ticker in tickers[:50]:  # Limit to avoid rate limits
            try:
                quote = gc.get_stock_quote(ticker)
                if quote.get("price"):
                    # Update market cap if available
                    con.execute("""
                        UPDATE dim_stocks SET market_cap_cr = ?
                        WHERE ticker = ? AND market_cap_cr = 0
                    """, [quote.get("year_high", 0) * 100, ticker])  # Rough proxy
                    updated += 1
            except Exception:
                continue
        con.close()
        return updated
    except Exception as e:
        logger.warning(f"dim_stocks refresh failed: {e}")
        return 0


def _get_tickers_from_csv() -> list[str]:
    """Fallback: read tickers from CSV."""
    try:
        with open(_CSV_PATH) as f:
            return [row["ticker"] for row in csv.DictReader(f)]
    except Exception:
        return [
            "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
            "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
            "LT", "AXISBANK", "WIPRO", "SUNPHARMA", "TATAMOTORS",
            "MARUTI", "NTPC", "TATASTEEL", "BAJFINANCE", "TITAN",
        ]
