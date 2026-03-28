"""
FII/DII institutional flow data connector.

Fetches daily FII/DII buy/sell data and detects flow patterns.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)


class FIIDIIConnector:
    """FII/DII flow data connector using NSE API."""

    NSE_BASE = "https://www.nseindia.com"
    _HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update(self._HEADERS)
        self._cookies_refreshed = False

    def _refresh_cookies(self):
        if self._cookies_refreshed:
            return
        try:
            self._session.get(self.NSE_BASE, timeout=10)
            self._cookies_refreshed = True
        except Exception:
            pass

    def get_daily_flows(self, days: int = 30) -> list[dict[str, Any]]:
        """Fetch daily FII/DII net purchase/sale data."""
        self._refresh_cookies()
        try:
            resp = self._session.get(
                f"{self.NSE_BASE}/api/fiidiiTradeReact", timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("data", [data])
            return []
        except Exception as e:
            logger.warning(f"FII/DII flow fetch failed: {e}")
            return []

    def detect_streak(self, flows: list[dict], entity: str = "fii", threshold_days: int = 5) -> dict:
        """Detect consecutive buying/selling streaks."""
        if not flows:
            return {"streak_days": 0, "direction": "none", "total_net_cr": 0}

        net_key = f"{entity}_net_cr" if f"{entity}_net_cr" in (flows[0] if flows else {}) else "netValue"
        streak = 0
        direction = None
        total = 0.0

        for flow in flows:
            net = float(flow.get(net_key, 0))
            if net > 0:
                if direction == "buy" or direction is None:
                    direction = "buy"
                    streak += 1
                    total += net
                else:
                    break
            elif net < 0:
                if direction == "sell" or direction is None:
                    direction = "sell"
                    streak += 1
                    total += net
                else:
                    break
            else:
                break

        return {
            "streak_days": streak,
            "direction": direction or "none",
            "total_net_cr": round(total, 2),
            "is_significant": streak >= threshold_days,
        }

    def detect_divergence(self, flows: list[dict]) -> dict:
        """Detect FII/DII divergence (opposing directions)."""
        if not flows or len(flows) < 5:
            return {"divergence": False, "detail": "Insufficient data"}

        recent = flows[:5]
        fii_net = sum(float(f.get("fii_net_cr", 0)) for f in recent)
        dii_net = sum(float(f.get("dii_net_cr", 0)) for f in recent)

        divergence = (fii_net > 0 and dii_net < 0) or (fii_net < 0 and dii_net > 0)

        return {
            "divergence": divergence,
            "fii_5d_net_cr": round(fii_net, 2),
            "dii_5d_net_cr": round(dii_net, 2),
            "detail": (
                f"FII {'buying' if fii_net > 0 else 'selling'} (₹{abs(fii_net):.0f} Cr) "
                f"while DII {'buying' if dii_net > 0 else 'selling'} (₹{abs(dii_net):.0f} Cr)"
                if divergence else "No divergence detected"
            ),
        }


_fii_dii_connector: Optional[FIIDIIConnector] = None


def get_fii_dii_connector() -> FIIDIIConnector:
    global _fii_dii_connector
    if _fii_dii_connector is None:
        _fii_dii_connector = FIIDIIConnector()
    return _fii_dii_connector
