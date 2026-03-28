"""
Groww API connector.

Uses JWT + TOTP authentication for Indian market data.
Provides stock quotes, search, and fundamentals via Groww's API.
"""
import logging
import time
from typing import Any, Optional

import requests

from src.connectors.base_connector import IndianDataSource, strip_suffix
from src.config import get_settings

logger = logging.getLogger(__name__)

try:
    import pyotp
    PYOTP_AVAILABLE = True
except ImportError:
    PYOTP_AVAILABLE = False

# Known Groww API base URLs (reverse-engineered)
GROWW_API_BASE = "https://groww.in/v1/api"
GROWW_SEARCH_URL = "https://groww.in/v1/api/search/v1/entity"
GROWW_STOCK_URL = "https://groww.in/v1/api/stocks_data/v1/accord_points/exchange/NSE/segment/CASH"


class GrowwConnector(IndianDataSource):
    """Groww API connector with JWT + TOTP auth."""

    def __init__(self):
        settings = get_settings()
        self._token = settings.groww_api_token
        self._totp_secret = settings.groww_totp_secret
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        self._authenticated = False

    @property
    def name(self) -> str:
        return "Groww"

    def _get_totp_code(self) -> str:
        """Generate current TOTP code from secret."""
        if not PYOTP_AVAILABLE or not self._totp_secret:
            return ""
        totp = pyotp.TOTP(self._totp_secret)
        return totp.now()

    def _ensure_auth(self) -> bool:
        """Set auth headers using JWT token."""
        if not self._token:
            logger.warning("Groww API token not configured")
            return False
        if self._authenticated:
            return True

        self._session.headers["Authorization"] = f"Bearer {self._token}"

        # If TOTP is configured, generate and add OTP header
        otp = self._get_totp_code()
        if otp:
            self._session.headers["X-Otp"] = otp

        self._authenticated = True
        return True

    def _api_get(self, url: str, params: dict = None) -> Optional[dict]:
        """Make authenticated GET request."""
        if not self._ensure_auth():
            return None
        try:
            resp = self._session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"Groww API failed: {e}")
            return None

    def get_stock_quote(self, symbol: str) -> dict[str, Any]:
        """Fetch stock quote from Groww."""
        clean = strip_suffix(symbol)
        data = self._api_get(
            f"{GROWW_STOCK_URL}/{clean}/latest",
        )
        if data:
            return {
                "ticker": clean,
                "price": data.get("ltp", data.get("close", 0)),
                "change": data.get("dayChange", 0),
                "change_pct": data.get("dayChangePerc", 0),
                "volume": data.get("volume", 0),
                "high": data.get("high", 0),
                "low": data.get("low", 0),
                "open": data.get("open", 0),
                "source": "Groww",
            }
        return {"ticker": clean, "price": 0, "error": "Groww API unavailable", "source": "Groww"}

    def get_historical_data(self, symbol: str, period: str = "1y"):
        """Groww doesn't provide bulk historical data — use NSE/yfinance instead."""
        import pandas as pd
        return pd.DataFrame()

    def search_stocks(self, query: str) -> list[dict]:
        """Search for stocks on Groww."""
        data = self._api_get(GROWW_SEARCH_URL, params={
            "page": "0",
            "query": query,
            "size": "10",
            "entity_type": "stocks",
        })
        if data and "content" in data:
            return [
                {
                    "ticker": item.get("nse_scrip_code", ""),
                    "name": item.get("title", ""),
                    "isin": item.get("isin", ""),
                    "source": "Groww",
                }
                for item in data["content"]
            ]
        return []

    def get_fundamentals(self, symbol: str) -> dict[str, Any]:
        """Fetch stock fundamentals from Groww."""
        clean = strip_suffix(symbol)
        data = self._api_get(
            f"{GROWW_API_BASE}/stocks_data/v1/company/search_id/{clean.lower()}/fundamental",
        )
        if data:
            ratios = data.get("ratios", {})
            return {
                "ticker": clean,
                "pe_ratio": ratios.get("peRatio", 0),
                "pb_ratio": ratios.get("pbRatio", 0),
                "dividend_yield": ratios.get("dividendYield", 0),
                "roe": ratios.get("roe", 0),
                "market_cap_cr": data.get("marketCap", 0) / 1e7 if data.get("marketCap") else 0,
                "source": "Groww",
            }
        return {"ticker": clean, "error": "Fundamentals unavailable", "source": "Groww"}


_groww_connector: Optional[GrowwConnector] = None


def get_groww_connector() -> GrowwConnector:
    """Get singleton Groww connector."""
    global _groww_connector
    if _groww_connector is None:
        _groww_connector = GrowwConnector()
        # Register with ConnectorRegistry
        from src.connectors.base_connector import get_registry
        get_registry().register(_groww_connector)
    return _groww_connector
