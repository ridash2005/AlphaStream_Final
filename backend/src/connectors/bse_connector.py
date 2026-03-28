"""
BSE India corporate announcements connector.

Fetches announcements, corporate actions, and company search from BSE API.
No API key needed — just proper headers.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import requests

from src.connectors.base_connector import IndianDataSource

logger = logging.getLogger(__name__)


class BSEConnector(IndianDataSource):
    """BSE India data connector."""

    BASE_URL = "https://api.bseindia.com/BseIndiaAPI/api"
    _HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.bseindia.com/",
    }

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update(self._HEADERS)

    @property
    def name(self) -> str:
        return "BSE"

    def get_stock_quote(self, symbol: str) -> dict[str, Any]:
        return {"ticker": symbol, "source": "BSE", "error": "Use NSE connector for quotes"}

    def get_historical_data(self, symbol: str, period: str = "1y"):
        import pandas as pd
        return pd.DataFrame()

    def get_announcements(self, scrip_code: str = "", days: int = 7) -> list[dict]:
        """Fetch corporate announcements from BSE."""
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        fmt = "%Y%m%d"

        try:
            url = f"{self.BASE_URL}/AnnSubCategoryGetData/w"
            params = {
                "strCat": "Company Update",
                "strPrevDate": from_date.strftime(fmt),
                "strToDate": to_date.strftime(fmt),
                "strScrip": scrip_code,
                "strSearch": "P",
                "strType": "C",
            }
            resp = self._session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, dict) and "Table" in data:
                return data["Table"]
            if isinstance(data, list):
                return data
            return []
        except Exception as e:
            logger.warning(f"BSE announcements failed: {e}")
            return []

    def get_corporate_actions(self, symbol: str = "", days: int = 30) -> list[dict]:
        """Fetch corporate actions (dividends, bonus, splits)."""
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        fmt = "%Y%m%d"

        try:
            url = f"{self.BASE_URL}/CorporateAction/w"
            params = {
                "scripcode": symbol,
                "index": "0",
                "from": from_date.strftime(fmt),
                "to": to_date.strftime(fmt),
            }
            resp = self._session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"BSE corporate actions failed: {e}")
            return []

    def search_company(self, query: str) -> list[dict]:
        """Search for a company by name on BSE."""
        try:
            url = f"{self.BASE_URL}/Suggest_new/w"
            params = {"flag": "2", "str": query}
            resp = self._session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"BSE search failed: {e}")
            return []


_bse_connector: Optional[BSEConnector] = None


def get_bse_connector() -> BSEConnector:
    global _bse_connector
    if _bse_connector is None:
        _bse_connector = BSEConnector()
    return _bse_connector
