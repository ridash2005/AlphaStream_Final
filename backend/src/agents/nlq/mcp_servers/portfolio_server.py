"""
Portfolio MCP Server — user holdings, P&L, portfolio-aware signals.
New for AlphaStream India (not in MediaFlowAI).
"""
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

import duckdb
from fastmcp import FastMCP

DB_PATH = str(pathlib.Path(__file__).parents[3] / "market_analytics.duckdb")

mcp = FastMCP("portfolio_server")
_conn = None
_holdings: list[dict] = []


def _db():
    global _conn
    if _conn is None:
        _conn = duckdb.connect(DB_PATH, read_only=True)
    return _conn


@mcp.tool()
def set_portfolio(holdings: list[dict]) -> dict:
    """
    Set user portfolio holdings.
    Args:
        holdings: [{ticker, quantity, buy_price}, ...]
    """
    global _holdings
    _holdings = holdings
    return {"status": "ok", "holdings_count": len(holdings)}


@mcp.tool()
def get_portfolio_summary() -> dict:
    """Get portfolio summary with current values and P&L."""
    if not _holdings:
        return {"error": "No portfolio set. Use set_portfolio first."}

    tickers = [h["ticker"] for h in _holdings]
    placeholders = ",".join(f"'{t}'" for t in tickers)

    prices = _db().execute(f"""
        SELECT ticker, close FROM (
            SELECT ticker, close, ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) AS rn
            FROM fact_daily_prices WHERE ticker IN ({placeholders})
        ) WHERE rn = 1
    """).fetchdf().set_index("ticker").to_dict(orient="index")

    total_invested = 0
    total_current = 0
    details = []

    for h in _holdings:
        ticker = h["ticker"]
        qty = h.get("quantity", 0)
        buy_price = h.get("buy_price", 0)
        current_price = prices.get(ticker, {}).get("close", buy_price)

        invested = qty * buy_price
        current = qty * current_price
        pnl = current - invested
        pnl_pct = (pnl / invested * 100) if invested else 0

        total_invested += invested
        total_current += current

        details.append({
            "ticker": ticker, "quantity": qty,
            "buy_price": buy_price, "current_price": round(current_price, 2),
            "invested": round(invested, 2), "current_value": round(current, 2),
            "pnl": round(pnl, 2), "pnl_pct": round(pnl_pct, 2),
        })

    return {
        "total_invested": round(total_invested, 2),
        "total_current": round(total_current, 2),
        "total_pnl": round(total_current - total_invested, 2),
        "total_pnl_pct": round((total_current - total_invested) / total_invested * 100, 2) if total_invested else 0,
        "holdings": details,
    }


@mcp.tool()
def get_portfolio_signals() -> list[dict]:
    """Get active signals affecting portfolio stocks."""
    if not _holdings:
        return [{"error": "No portfolio set"}]

    tickers = [h["ticker"] for h in _holdings]
    placeholders = ",".join(f"'{t}'" for t in tickers)

    return _db().execute(f"""
        SELECT * FROM v_signal_summary
        WHERE ticker IN ({placeholders})
          AND signal_date >= current_date - INTERVAL '7 days'
        ORDER BY alpha_score DESC
    """).fetchdf().to_dict(orient="records")


if __name__ == "__main__":
    mcp.run()
