"""
NSE India data connector.

Primary: yfinance with .NS suffix (most reliable, no auth needed).
Secondary: Direct NSE API with cookie-based auth (for PIT/SAST/bulk deals).
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Optional

import pandas as pd
import requests

from src.connectors.base_connector import IndianDataSource, ensure_ns_suffix, strip_suffix

logger = logging.getLogger(__name__)

# Optional imports
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance not installed.")


class NSEConnector(IndianDataSource):
    """NSE India data connector using yfinance + direct NSE API fallback."""

    _instance: Optional["NSEConnector"] = None

    NSE_BASE = "https://www.nseindia.com"
    NSE_API = "https://www.nseindia.com/api"
    _HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    }

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update(self._HEADERS)
        self._cookies_ts: float = 0
        self._cache: dict[str, tuple[float, Any]] = {}
        self._cache_ttl = 300  # 5 min cache

    @property
    def name(self) -> str:
        return "NSE"

    # ── Cookie management ──────────────────────────────────────

    def _refresh_cookies(self) -> None:
        """Hit NSE homepage to get session cookies (required for API)."""
        if time.time() - self._cookies_ts < 120:
            return  # Cookies still fresh
        try:
            self._session.get(self.NSE_BASE, timeout=10)
            self._cookies_ts = time.time()
            logger.debug("NSE cookies refreshed")
        except Exception as e:
            logger.warning(f"Failed to refresh NSE cookies: {e}")

    def _nse_get(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make authenticated GET to NSE API."""
        self._refresh_cookies()
        try:
            url = f"{self.NSE_API}/{endpoint}"
            resp = self._session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"NSE API {endpoint} failed: {e}")
            return None

    # ── Cache helper ───────────────────────────────────────────

    def _cached(self, key: str):
        """Return cached value if still valid."""
        if key in self._cache:
            ts, val = self._cache[key]
            if time.time() - ts < self._cache_ttl:
                return val
        return None

    def _set_cache(self, key: str, val: Any):
        self._cache[key] = (time.time(), val)

    # ── Public API ─────────────────────────────────────────────

    def get_stock_quote(self, symbol: str) -> dict[str, Any]:
        """Fetch current quote. Primary: yfinance, fallback: NSE API."""
        cache_key = f"quote:{symbol}"
        cached = self._cached(cache_key)
        if cached:
            return cached

        clean = strip_suffix(symbol)

        # Try yfinance first (most reliable)
        if YFINANCE_AVAILABLE:
            try:
                tk = yf.Ticker(ensure_ns_suffix(clean))
                info = tk.fast_info
                result = {
                    "ticker": clean,
                    "price": float(info.last_price) if hasattr(info, "last_price") else 0,
                    "change": float(info.last_price - info.previous_close) if hasattr(info, "previous_close") else 0,
                    "change_pct": round(
                        ((info.last_price - info.previous_close) / info.previous_close) * 100, 2
                    ) if hasattr(info, "previous_close") and info.previous_close else 0,
                    "volume": int(info.last_volume) if hasattr(info, "last_volume") else 0,
                    "market_cap_cr": round(info.market_cap / 1e7, 2) if hasattr(info, "market_cap") and info.market_cap else 0,
                    "source": "yfinance",
                }
                self._set_cache(cache_key, result)
                return result
            except Exception as e:
                logger.debug(f"yfinance quote failed for {clean}: {e}")

        # Fallback: NSE API
        data = self._nse_get("quote-equity", {"symbol": clean})
        if data and "priceInfo" in data:
            pi = data["priceInfo"]
            result = {
                "ticker": clean,
                "price": pi.get("lastPrice", 0),
                "change": pi.get("change", 0),
                "change_pct": pi.get("pChange", 0),
                "volume": data.get("preOpenMarket", {}).get("totalTradedVolume", 0),
                "market_cap_cr": 0,
                "source": "NSE_API",
            }
            self._set_cache(cache_key, result)
            return result

        return {"ticker": clean, "price": 0, "error": "No data available", "source": "none"}

    def get_historical_data(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        """Fetch historical OHLCV data via yfinance."""
        if not YFINANCE_AVAILABLE:
            return pd.DataFrame()
        try:
            tk = yf.Ticker(ensure_ns_suffix(strip_suffix(symbol)))
            hist = tk.history(period=period, interval="1d")
            return hist
        except Exception as e:
            logger.error(f"Historical data failed for {symbol}: {e}")
            return pd.DataFrame()

    def get_insider_trades(self, symbol: str = "", days: int = 90) -> list[dict]:
        """Fetch PIT (Prohibition of Insider Trading) data from NSE."""
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        fmt = "%d-%m-%Y"

        params = {
            "index": "equities",
            "from_date": from_date.strftime(fmt),
            "to_date": to_date.strftime(fmt),
        }
        data = self._nse_get("corporates-pit", params)
        if not data or "data" not in data:
            return []

        trades = data["data"]
        if symbol:
            clean = strip_suffix(symbol)
            trades = [t for t in trades if t.get("symbol", "") == clean]
        return [self.normalize_trade(t) for t in trades]

    def get_sast_data(self, symbol: str = "", days: int = 90) -> list[dict]:
        """Fetch SAST (Substantial Acquisition) data from NSE."""
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        fmt = "%d-%m-%Y"

        params = {
            "index": "equities",
            "from_date": from_date.strftime(fmt),
            "to_date": to_date.strftime(fmt),
        }
        data = self._nse_get("corporates-sast", params)
        if not data or "data" not in data:
            return []

        records = data["data"]
        if symbol:
            clean = strip_suffix(symbol)
            records = [r for r in records if r.get("symbol", "") == clean]
        return records

    def get_bulk_deals(self, days: int = 30) -> list[dict]:
        """Fetch bulk deal data from NSE."""
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        fmt = "%d-%m-%Y"

        params = {
            "from": from_date.strftime(fmt),
            "to": to_date.strftime(fmt),
        }
        data = self._nse_get("historical/bulk-deals", params)
        if not data:
            return []
        return data if isinstance(data, list) else data.get("data", [])

    def get_block_deals(self, days: int = 7) -> list[dict]:
        """Fetch block deal data from NSE."""
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        fmt = "%d-%m-%Y"

        params = {
            "from": from_date.strftime(fmt),
            "to": to_date.strftime(fmt),
        }
        data = self._nse_get("historical/block-deals", params)
        if not data:
            return []
        return data if isinstance(data, list) else data.get("data", [])

    def get_fii_dii_data(self) -> Optional[dict]:
        """Fetch FII/DII trading activity."""
        return self._nse_get("fiidiiTradeReact")

    def normalize_trade(self, raw: dict) -> dict[str, Any]:
        """Normalize NSE PIT/SAST trade to standard format."""
        return {
            "ticker": raw.get("symbol", ""),
            "person_name": raw.get("acqName", raw.get("acquirerName", "")),
            "person_category": raw.get("personCategory", raw.get("category", "")),
            "trade_type": "buy" if raw.get("secAcq", 0) > 0 or "buy" in str(raw.get("transactionType", "")).lower() else "sell",
            "quantity": abs(int(raw.get("secAcq", 0) or raw.get("secDisp", 0) or raw.get("noOfShares", 0))),
            "value_lakhs": round(float(raw.get("secVal", 0) or 0) / 1e5, 2),
            "trade_date": raw.get("date", raw.get("intimationDate", "")),
            "source": "NSE",
        }


_nse_connector: Optional[NSEConnector] = None


def get_nse_connector() -> NSEConnector:
    """Get singleton NSE connector."""
    global _nse_connector
    if _nse_connector is None:
        _nse_connector = NSEConnector()
    return _nse_connector
