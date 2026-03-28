"""
Portfolio Manager — user holdings, P&L, portfolio context for NLQ/RAG.
"""
import logging
from typing import Any, Optional

from src.connectors.base_connector import ensure_ns_suffix

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


class PortfolioManager:
    """Manages user portfolio for context injection into NLQ/RAG."""

    def __init__(self):
        self.holdings: list[dict] = []

    def set_holdings(self, holdings: list[dict]) -> None:
        """Set user's portfolio. Each: {ticker, quantity, buy_price}."""
        self.holdings = holdings
        logger.info(f"Portfolio set: {len(holdings)} holdings")

    def get_portfolio_context(self) -> str:
        """Generate context string for RAG/NLQ system prompt injection."""
        if not self.holdings:
            return ""

        lines = ["User's portfolio:"]
        total_invested = 0
        total_current = 0

        for h in self.holdings:
            ticker = h["ticker"]
            qty = h.get("quantity", 0)
            buy_price = h.get("buy_price", 0)
            current = self._get_current_price(ticker) or buy_price
            invested = qty * buy_price
            current_val = qty * current
            pnl_pct = ((current - buy_price) / buy_price * 100) if buy_price else 0

            total_invested += invested
            total_current += current_val
            lines.append(
                f"  {qty} {ticker} @ ₹{buy_price:.0f} (current: ₹{current:.0f}, P&L: {pnl_pct:+.1f}%)"
            )

        total_pnl = ((total_current - total_invested) / total_invested * 100) if total_invested else 0
        lines.append(f"  Total: ₹{total_current:,.0f} invested ₹{total_invested:,.0f} (P&L: {total_pnl:+.1f}%)")
        return "\n".join(lines)

    def get_portfolio_value(self) -> dict[str, Any]:
        """Calculate total portfolio value and P&L."""
        if not self.holdings:
            return {"error": "No portfolio set"}

        details = []
        total_invested = 0
        total_current = 0

        for h in self.holdings:
            ticker = h["ticker"]
            qty = h.get("quantity", 0)
            buy_price = h.get("buy_price", 0)
            current = self._get_current_price(ticker) or buy_price
            invested = qty * buy_price
            current_val = qty * current
            pnl = current_val - invested

            total_invested += invested
            total_current += current_val

            details.append({
                "ticker": ticker,
                "quantity": qty,
                "buy_price": buy_price,
                "current_price": round(current, 2),
                "invested": round(invested, 2),
                "current_value": round(current_val, 2),
                "pnl": round(pnl, 2),
                "pnl_pct": round((pnl / invested * 100) if invested else 0, 2),
            })

        return {
            "total_invested": round(total_invested, 2),
            "total_current": round(total_current, 2),
            "total_pnl": round(total_current - total_invested, 2),
            "total_pnl_pct": round(((total_current - total_invested) / total_invested * 100) if total_invested else 0, 2),
            "holdings": details,
        }

    def get_tickers(self) -> list[str]:
        """Return tickers in portfolio."""
        return [h["ticker"] for h in self.holdings]

    def get_concentration_warnings(self) -> list[str]:
        """Check sector concentration and return warnings."""
        if not self.holdings:
            return []

        import csv
        from pathlib import Path
        csv_path = Path(__file__).resolve().parents[1] / "data" / "nifty50_symbols.csv"
        sector_map = {}
        try:
            with open(csv_path) as f:
                for row in csv.DictReader(f):
                    sector_map[row["ticker"]] = row["sector"]
        except Exception:
            return []

        sector_value: dict[str, float] = {}
        total = 0
        for h in self.holdings:
            sector = sector_map.get(h["ticker"], "Unknown")
            price = self._get_current_price(h["ticker"]) or h.get("buy_price", 0)
            val = h.get("quantity", 0) * price
            sector_value[sector] = sector_value.get(sector, 0) + val
            total += val

        warnings = []
        if total > 0:
            for sector, val in sorted(sector_value.items(), key=lambda x: -x[1]):
                pct = val / total * 100
                if pct > 30:
                    warnings.append(
                        f"High concentration: {pct:.0f}% of your portfolio is in {sector} "
                        f"(recommended max 30%). Consider diversifying."
                    )
        return warnings

    def _get_current_price(self, ticker: str) -> Optional[float]:
        """Fetch current price via yfinance."""
        if not YFINANCE_AVAILABLE:
            return None
        try:
            tk = yf.Ticker(ensure_ns_suffix(ticker))
            info = tk.fast_info
            return float(info.last_price) if hasattr(info, "last_price") else None
        except Exception:
            return None
