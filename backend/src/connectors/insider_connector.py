"""
NSE Insider Trading connector (SAST/PIT regulations).

Replaces SEC connector for Indian market insider trade data.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import requests

from src.connectors.base_connector import IndianDataSource, strip_suffix

logger = logging.getLogger(__name__)


class InsiderConnector(IndianDataSource):
    """NSE Insider Trading data (SAST + PIT)."""

    NSE_BASE = "https://www.nseindia.com"
    NSE_API = "https://www.nseindia.com/api"
    _HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update(self._HEADERS)
        self._cookies_refreshed = False

    @property
    def name(self) -> str:
        return "NSE_Insider"

    def _refresh_cookies(self):
        if self._cookies_refreshed:
            return
        try:
            self._session.get(self.NSE_BASE, timeout=10)
            self._cookies_refreshed = True
        except Exception:
            pass

    def _api_get(self, endpoint: str, params: dict = None) -> Optional[list]:
        self._refresh_cookies()
        try:
            resp = self._session.get(f"{self.NSE_API}/{endpoint}", params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"NSE insider API {endpoint} failed: {e}")
            return []

    def get_stock_quote(self, symbol: str) -> dict[str, Any]:
        return {"ticker": symbol, "source": "NSE_Insider", "error": "Use NSE connector"}

    def get_historical_data(self, symbol: str, period: str = "1y"):
        import pandas as pd
        return pd.DataFrame()

    def get_pit_data(self, symbol: str = "", days: int = 90) -> list[dict]:
        """Fetch PIT (Prohibition of Insider Trading) data."""
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        fmt = "%d-%m-%Y"
        params = {
            "index": "equities",
            "from_date": from_date.strftime(fmt),
            "to_date": to_date.strftime(fmt),
        }
        data = self._api_get("corporates-pit", params) or []
        if symbol:
            clean = strip_suffix(symbol)
            data = [d for d in data if d.get("symbol", "") == clean]
        return [self.normalize_trade(d) for d in data]

    def get_sast_data(self, symbol: str = "", days: int = 90) -> list[dict]:
        """Fetch SAST (Substantial Acquisition) data."""
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        fmt = "%d-%m-%Y"
        params = {
            "index": "equities",
            "from_date": from_date.strftime(fmt),
            "to_date": to_date.strftime(fmt),
        }
        data = self._api_get("corporates-sast", params) or []
        if symbol:
            clean = strip_suffix(symbol)
            data = [d for d in data if d.get("symbol", "") == clean]
        return data

    def get_insider_trades(self, symbol: str = "", days: int = 90) -> list[dict]:
        """Combined PIT + bulk deals for a symbol."""
        trades = self.get_pit_data(symbol, days)
        bulk = self.get_bulk_deals(days)
        if symbol:
            clean = strip_suffix(symbol)
            bulk = [b for b in bulk if b.get("symbol", "") == clean]
        return trades + [self.normalize_trade(b) for b in bulk]

    def get_bulk_deals(self, days: int = 30) -> list[dict]:
        """Fetch bulk deal data."""
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        fmt = "%d-%m-%Y"
        return self._api_get("historical/bulk-deals", {
            "from": from_date.strftime(fmt), "to": to_date.strftime(fmt)
        }) or []

    def get_block_deals(self, days: int = 7) -> list[dict]:
        """Fetch block deal data."""
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        fmt = "%d-%m-%Y"
        return self._api_get("historical/block-deals", {
            "from": from_date.strftime(fmt), "to": to_date.strftime(fmt)
        }) or []

    def normalize_trade(self, raw: dict) -> dict[str, Any]:
        return {
            "ticker": raw.get("symbol", ""),
            "person_name": raw.get("acqName", raw.get("clientName", "")),
            "person_category": raw.get("personCategory", raw.get("category", "")),
            "trade_type": "buy" if raw.get("secAcq", 0) > 0 or "buy" in str(raw.get("transactionType", "")).lower() else "sell",
            "quantity": abs(int(raw.get("secAcq", 0) or raw.get("secDisp", 0) or raw.get("qty", 0))),
            "value_lakhs": round(float(raw.get("secVal", 0) or 0) / 1e5, 2),
            "trade_date": raw.get("date", raw.get("intimationDate", "")),
            "source": "NSE",
        }


_insider_connector: Optional[InsiderConnector] = None


def get_insider_connector() -> InsiderConnector:
    global _insider_connector
    if _insider_connector is None:
        _insider_connector = InsiderConnector()
    return _insider_connector
