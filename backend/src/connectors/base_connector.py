"""
Base connector interfaces for Indian market data sources.

Provides abstract IndianDataSource and ConnectorRegistry for pluggable data sources.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def ensure_ns_suffix(ticker: str) -> str:
    """Append .NS suffix for NSE tickers if not already present."""
    if not ticker.endswith((".NS", ".BO")):
        return f"{ticker}.NS"
    return ticker


def strip_suffix(ticker: str) -> str:
    """Remove .NS or .BO suffix from ticker."""
    for suffix in (".NS", ".BO"):
        if ticker.endswith(suffix):
            return ticker[: -len(suffix)]
    return ticker


class IndianDataSource(ABC):
    """Abstract base for Indian market data connectors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Connector name (e.g., 'NSE', 'BSE', 'Groww')."""
        ...

    @abstractmethod
    def get_stock_quote(self, symbol: str) -> dict[str, Any]:
        """Fetch current quote for a stock."""
        ...

    @abstractmethod
    def get_historical_data(
        self, symbol: str, period: str = "1y"
    ) -> pd.DataFrame:
        """Fetch historical OHLCV data."""
        ...

    def get_insider_trades(self, symbol: str = "", days: int = 90) -> list[dict]:
        """Fetch insider trading data. Override in connectors that support it."""
        return []

    def get_corporate_actions(self, symbol: str = "", days: int = 30) -> list[dict]:
        """Fetch corporate actions. Override in connectors that support it."""
        return []

    def normalize_trade(self, raw: dict) -> dict[str, Any]:
        """Normalize a trade record to standard format."""
        return {
            "ticker": raw.get("symbol", raw.get("ticker", "")),
            "person_name": raw.get("person_name", raw.get("acquirerName", "")),
            "person_category": raw.get("person_category", raw.get("category", "")),
            "trade_type": raw.get("trade_type", raw.get("transactionType", "")),
            "quantity": raw.get("quantity", raw.get("noOfShares", 0)),
            "value_lakhs": raw.get("value_lakhs", 0),
            "trade_date": raw.get("trade_date", raw.get("date", "")),
            "source": self.name,
        }


class ConnectorRegistry:
    """Registry for pluggable data source connectors."""

    _instance: Optional["ConnectorRegistry"] = None
    _sources: dict[str, IndianDataSource]

    def __new__(cls) -> "ConnectorRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._sources = {}
        return cls._instance

    def register(self, source: IndianDataSource) -> None:
        """Register a data source connector."""
        self._sources[source.name] = source
        logger.info(f"Registered data source: {source.name}")

    def get(self, name: str) -> Optional[IndianDataSource]:
        """Get a connector by name."""
        return self._sources.get(name)

    def get_all(self) -> list[IndianDataSource]:
        """Get all registered connectors."""
        return list(self._sources.values())

    def names(self) -> list[str]:
        """List registered connector names."""
        return list(self._sources.keys())


def get_registry() -> ConnectorRegistry:
    """Get the singleton ConnectorRegistry."""
    return ConnectorRegistry()
