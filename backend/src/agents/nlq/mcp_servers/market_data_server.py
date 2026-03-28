"""
Market Data MCP Server — stock quotes, signals, fundamentals.
Replaces MediaFlowAI's kpi_server for financial domain.
"""
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

import yaml
import duckdb
from fastmcp import FastMCP

DB_PATH = str(pathlib.Path(__file__).parents[3] / "market_analytics.duckdb")
CONFIG_PATH = pathlib.Path(__file__).parents[4] / "config" / "signal_registry.yaml"

mcp = FastMCP("market_data_server")
_conn = None


def _db():
    global _conn
    if _conn is None:
        _conn = duckdb.connect(DB_PATH, read_only=True)
    return _conn


def _registry() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f).get("signals", {})


@mcp.tool()
def get_stock_quote(ticker: str) -> dict:
    """Get latest price data for a stock ticker."""
    rows = _db().execute("""
        SELECT d.ticker, d.company_name, d.sector, d.market_cap_cr,
               p.close, p.volume, p.date
        FROM dim_stocks d
        LEFT JOIN (
            SELECT ticker, close, volume, date,
                   ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) AS rn
            FROM fact_daily_prices
        ) p ON d.ticker = p.ticker AND p.rn = 1
        WHERE d.ticker = ?
    """, [ticker.upper()]).fetchdf().to_dict(orient="records")
    return rows[0] if rows else {"error": f"Ticker {ticker} not found"}


@mcp.tool()
def get_latest_signals(top_n: int = 10, sector: str = "") -> list[dict]:
    """Get top N signals by alpha score, optionally filtered by sector."""
    sql = "SELECT * FROM v_signal_summary WHERE signal_date >= current_date - INTERVAL '7 days'"
    if sector:
        sql += f" AND sector = '{sector}'"
    sql += f" ORDER BY alpha_score DESC LIMIT {top_n}"
    return _db().execute(sql).fetchdf().to_dict(orient="records")


@mcp.tool()
def get_insider_activity(ticker: str = "", days: int = 30) -> list[dict]:
    """Get insider trading activity, optionally for a specific ticker."""
    sql = f"SELECT * FROM v_insider_activity_30d WHERE trade_date >= current_date - INTERVAL '{days} days'"
    if ticker:
        sql += f" AND ticker = '{ticker.upper()}'"
    sql += " ORDER BY trade_date DESC LIMIT 50"
    return _db().execute(sql).fetchdf().to_dict(orient="records")


@mcp.tool()
def get_fii_dii_summary(days: int = 30) -> list[dict]:
    """Get FII/DII flow summary with rolling trends."""
    return _db().execute(f"""
        SELECT * FROM v_fii_dii_trend
        WHERE date >= current_date - INTERVAL '{days} days'
        ORDER BY date DESC
    """).fetchdf().to_dict(orient="records")


@mcp.tool()
def get_sector_heatmap() -> list[dict]:
    """Get sector-wise signal counts and average alpha scores."""
    return _db().execute("SELECT * FROM v_sector_heatmap").fetchdf().to_dict(orient="records")


@mcp.tool()
def list_available_signals() -> list[dict]:
    """List all signal types tracked by AlphaStream India."""
    registry = _registry()
    return [
        {"name": v.get("name", k), "key": k, "description": v.get("description", ""), "page": v.get("page", "")}
        for k, v in registry.items()
    ]


if __name__ == "__main__":
    mcp.run()
