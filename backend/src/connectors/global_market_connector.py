"""
Global Market Connector — WorldMonitor integration backbone.

Fetches global indices, commodities, VIX, Fear & Greed, sector performance,
crypto, and INR/USD using yfinance + CNN Fear & Greed API.
Reads symbol universes from WorldMonitor's shared JSON configs.

Two-tier cache: FAST (5min) for quotes, SLOW (30min) for structural data.
Circuit breaker: serves stale data up to 1hr if upstream fails.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# ── Symbol universes from WorldMonitor ──────────────────────────────

_WM_ROOT = Path(__file__).resolve().parents[3] / "worldmonitor" / "shared"


def _load_wm_json(filename: str) -> dict:
    path = _WM_ROOT / filename
    if path.exists():
        with open(path) as f:
            return json.load(f)
    logger.warning(f"WorldMonitor config not found: {path}")
    return {}


def _build_indices() -> list[dict]:
    """Load global indices from WorldMonitor stocks.json, fall back to hardcoded."""
    wm = _load_wm_json("stocks.json")
    if wm.get("symbols"):
        # Extract indices (start with ^) + first 5 Indian stocks
        indices = [s for s in wm["symbols"] if s["symbol"].startswith("^")]
        return indices[:10]  # cap at 10
    return [
        {"symbol": "^GSPC", "name": "S&P 500", "display": "SPX"},
        {"symbol": "^DJI", "name": "Dow Jones", "display": "DOW"},
        {"symbol": "^IXIC", "name": "NASDAQ", "display": "NDX"},
        {"symbol": "^NSEI", "name": "Nifty 50", "display": "NIFTY"},
        {"symbol": "^BSESN", "name": "BSE Sensex", "display": "SENSEX"},
        {"symbol": "^FTSE", "name": "FTSE 100", "display": "FTSE"},
        {"symbol": "^N225", "name": "Nikkei 225", "display": "NIKKEI"},
        {"symbol": "^HSI", "name": "Hang Seng", "display": "HSI"},
    ]


def _build_commodities() -> list[dict]:
    """Load commodities from WorldMonitor commodities.json."""
    wm = _load_wm_json("commodities.json")
    if wm.get("commodities"):
        return wm["commodities"][:12]  # cap at 12
    return [
        {"symbol": "GC=F", "name": "Gold", "display": "GOLD"},
        {"symbol": "SI=F", "name": "Silver", "display": "SILVER"},
        {"symbol": "CL=F", "name": "Crude Oil WTI", "display": "OIL"},
        {"symbol": "BZ=F", "name": "Brent Crude", "display": "BRENT"},
        {"symbol": "NG=F", "name": "Natural Gas", "display": "NATGAS"},
        {"symbol": "HG=F", "name": "Copper", "display": "COPPER"},
        {"symbol": "ZW=F", "name": "Wheat", "display": "WHEAT"},
        {"symbol": "CT=F", "name": "Cotton", "display": "COTTON"},
    ]


def _build_sectors() -> list[dict]:
    """Load sector ETFs from WorldMonitor sectors.json."""
    wm = _load_wm_json("sectors.json")
    if wm.get("sectors"):
        return wm["sectors"]
    return [
        {"symbol": "XLK", "name": "Technology"},
        {"symbol": "XLF", "name": "Financials"},
        {"symbol": "XLE", "name": "Energy"},
        {"symbol": "XLV", "name": "Health Care"},
        {"symbol": "XLY", "name": "Consumer Disc."},
        {"symbol": "XLI", "name": "Industrials"},
        {"symbol": "XLP", "name": "Con. Staples"},
        {"symbol": "XLU", "name": "Utilities"},
        {"symbol": "XLB", "name": "Materials"},
        {"symbol": "XLRE", "name": "Real Estate"},
        {"symbol": "XLC", "name": "Comm. Svcs"},
        {"symbol": "SMH", "name": "Semiconductors"},
    ]


def _build_crypto() -> list[dict]:
    """Load crypto from WorldMonitor crypto.json, map to yfinance symbols."""
    wm = _load_wm_json("crypto.json")
    meta = wm.get("meta", {})
    if meta:
        return [
            {"symbol": f"{v['symbol']}-USD", "name": v["name"], "display": v["symbol"]}
            for v in list(meta.values())[:6]
        ]
    return [
        {"symbol": "BTC-USD", "name": "Bitcoin", "display": "BTC"},
        {"symbol": "ETH-USD", "name": "Ethereum", "display": "ETH"},
        {"symbol": "SOL-USD", "name": "Solana", "display": "SOL"},
        {"symbol": "XRP-USD", "name": "XRP", "display": "XRP"},
    ]


# Build from WorldMonitor JSON on import
GLOBAL_INDICES = _build_indices()
KEY_COMMODITIES = _build_commodities()
SECTOR_ETFS = _build_sectors()
CRYPTO_SYMBOLS = _build_crypto()

# INR/USD and DXY for currency context
CURRENCY_SYMBOLS = [
    {"symbol": "INR=X", "name": "USD/INR", "display": "USD/INR"},
    {"symbol": "DX-Y.NYB", "name": "US Dollar Index", "display": "DXY"},
]

# ── Cache ────────────────────────────────────────────────────────────

FAST_TTL = 300     # 5 min — quotes, VIX
SLOW_TTL = 1800    # 30 min — Fear & Greed, sectors
STALE_TTL = 3600   # 1 hr — circuit breaker fallback


class _CacheEntry:
    __slots__ = ("data", "fetched_at")

    def __init__(self, data: Any, fetched_at: float):
        self.data = data
        self.fetched_at = fetched_at

    def is_fresh(self, ttl: float) -> bool:
        return (time.time() - self.fetched_at) < ttl

    def is_stale(self) -> bool:
        return (time.time() - self.fetched_at) >= STALE_TTL


class GlobalMarketConnector:
    """Fetches global market data for AlphaStream India context enrichment."""

    _instance: Optional["GlobalMarketConnector"] = None

    def __init__(self):
        self._cache: dict[str, _CacheEntry] = {}

    @classmethod
    def get_instance(cls) -> "GlobalMarketConnector":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Private helpers ──────────────────────────────────────────

    def _get_cached(self, key: str, ttl: float) -> Any | None:
        entry = self._cache.get(key)
        if entry and entry.is_fresh(ttl):
            return entry.data
        return None

    def _get_stale(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if entry and not entry.is_stale():
            return entry.data
        return None

    def _set_cache(self, key: str, data: Any) -> None:
        self._cache[key] = _CacheEntry(data, time.time())

    def _fetch_yf_quotes(self, symbols: list[dict]) -> list[dict]:
        """Fetch batch quotes via yfinance."""
        try:
            import yfinance as yf
        except ImportError:
            logger.warning("yfinance not available for global quotes")
            return []

        ticker_str = " ".join(s["symbol"] for s in symbols)
        results = []
        try:
            tickers = yf.Tickers(ticker_str)
            for sym_info in symbols:
                sym = sym_info["symbol"]
                try:
                    ticker = tickers.tickers.get(sym)
                    if not ticker:
                        continue
                    info = ticker.fast_info
                    price = getattr(info, "last_price", None)
                    prev_close = getattr(info, "previous_close", None)
                    change = 0.0
                    if price and prev_close and prev_close != 0:
                        change = ((price - prev_close) / prev_close) * 100

                    # Sparkline from last 5 days
                    sparkline = []
                    try:
                        hist = ticker.history(period="5d", interval="1d")
                        if hist is not None and not hist.empty:
                            sparkline = hist["Close"].dropna().tolist()[-5:]
                    except Exception:
                        pass

                    results.append({
                        "symbol": sym,
                        "name": sym_info["name"],
                        "display": sym_info.get("display", sym),
                        "price": round(price, 2) if price else None,
                        "change": round(change, 2),
                        "sparkline": [round(v, 2) for v in sparkline],
                    })
                except Exception as e:
                    logger.debug(f"Failed to fetch {sym}: {e}")
        except Exception as e:
            logger.warning(f"yfinance batch fetch failed: {e}")

        return results

    def _cached_fetch(self, key: str, ttl: float, symbols: list[dict]) -> list[dict]:
        """Generic cached yfinance fetch."""
        cached = self._get_cached(key, ttl)
        if cached:
            return cached
        data = self._fetch_yf_quotes(symbols)
        if data:
            self._set_cache(key, data)
        else:
            stale = self._get_stale(key)
            if stale:
                return stale
        return data

    # ── Public API ───────────────────────────────────────────────

    def get_global_indices(self) -> list[dict]:
        """Global stock indices with price, change%, sparkline."""
        return self._cached_fetch("indices", FAST_TTL, GLOBAL_INDICES)

    def get_commodity_quotes(self) -> list[dict]:
        """Commodity futures quotes."""
        return self._cached_fetch("commodities", FAST_TTL, KEY_COMMODITIES)

    def get_crypto_quotes(self) -> list[dict]:
        """Top crypto quotes."""
        return self._cached_fetch("crypto", FAST_TTL, CRYPTO_SYMBOLS)

    def get_sector_performance(self) -> list[dict]:
        """US sector ETF performance."""
        return self._cached_fetch("sectors", SLOW_TTL, SECTOR_ETFS)

    def get_currency_quotes(self) -> list[dict]:
        """INR/USD and DXY quotes."""
        return self._cached_fetch("currencies", FAST_TTL, CURRENCY_SYMBOLS)

    def get_vix(self) -> dict:
        """VIX current value + status classification."""
        cached = self._get_cached("vix", FAST_TTL)
        if cached:
            return cached

        try:
            import yfinance as yf
            vix = yf.Ticker("^VIX")
            info = vix.fast_info
            price = getattr(info, "last_price", None)
            prev = getattr(info, "previous_close", None)
            change = 0.0
            if price and prev and prev != 0:
                change = ((price - prev) / prev) * 100

            # Classify VIX
            status = "UNKNOWN"
            if price is not None:
                if price < 15:
                    status = "LOW"
                elif price < 20:
                    status = "MODERATE"
                elif price < 30:
                    status = "HIGH"
                else:
                    status = "EXTREME"

            result = {
                "value": round(price, 2) if price else None,
                "change": round(change, 2),
                "status": status,
            }
            self._set_cache("vix", result)
            return result
        except Exception as e:
            logger.warning(f"VIX fetch failed: {e}")
            stale = self._get_stale("vix")
            return stale or {"value": None, "change": 0, "status": "UNKNOWN"}

    def get_fear_greed(self) -> dict:
        """Fear & Greed Index (0-100 + label).

        Tries CNN first; falls back to alternative.me (free, no key required)
        if CNN returns 4xx/5xx or times out.
        """
        cached = self._get_cached("fear_greed", SLOW_TTL)
        if cached:
            return cached

        def _score_to_label(score: float) -> str:
            if score <= 25:
                return "Extreme Fear"
            if score <= 45:
                return "Fear"
            if score <= 55:
                return "Neutral"
            if score <= 75:
                return "Greed"
            return "Extreme Greed"

        with httpx.Client(timeout=10.0) as client:
            # ── Source 1: CNN Fear & Greed ────────────────────────────────
            try:
                resp = client.get(
                    "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                )
                resp.raise_for_status()
                fg = resp.json().get("fear_and_greed", {})
                score = float(fg.get("score", 0))
                if score > 0:
                    result = {
                        "score": round(score, 1),
                        "label": _score_to_label(score),
                        "previous": round(float(fg.get("previous_close", score)), 1),
                        "timestamp": fg.get("timestamp", ""),
                        "source": "CNN",
                    }
                    self._set_cache("fear_greed", result)
                    return result
            except Exception as e:
                logger.debug(f"CNN Fear & Greed unavailable ({e}), trying alternative.me")

            # ── Source 2: alternative.me (free, no key) ───────────────────
            try:
                resp = client.get("https://api.alternative.me/fng/?limit=2", timeout=8.0)
                resp.raise_for_status()
                entries = resp.json().get("data", [])
                if entries:
                    cur = entries[0]
                    prev = entries[1] if len(entries) > 1 else cur
                    score = float(cur["value"])
                    result = {
                        "score": round(score, 1),
                        "label": cur.get("value_classification", _score_to_label(score)),
                        "previous": round(float(prev["value"]), 1),
                        "timestamp": cur.get("timestamp", ""),
                        "source": "alternative.me",
                    }
                    self._set_cache("fear_greed", result)
                    return result
            except Exception as e:
                logger.warning(f"alternative.me Fear & Greed also failed: {e}")

        stale = self._get_stale("fear_greed")
        return stale or {"score": 50, "label": "Neutral", "previous": 50, "timestamp": "", "source": "fallback"}

    def get_decision_context(self) -> dict:
        """Combined context blob for the Decision Agent prompt."""
        vix = self.get_vix()
        fg = self.get_fear_greed()
        indices = self.get_global_indices()
        commodities = self.get_commodity_quotes()
        currencies = self.get_currency_quotes()
        crypto = self.get_crypto_quotes()

        # Extract key values
        sp500_change = next((i["change"] for i in indices if i["symbol"] == "^GSPC"), 0)
        nifty_change = next((i["change"] for i in indices if i["symbol"] == "^NSEI"), 0)
        crude_change = next((c["change"] for c in commodities if c["symbol"] == "CL=F"), 0)
        gold_change = next((c["change"] for c in commodities if c["symbol"] == "GC=F"), 0)
        brent_price = next((c["price"] for c in commodities if c["symbol"] == "BZ=F"), None)
        usd_inr = next((c["price"] for c in currencies if c["symbol"] == "INR=X"), None)
        dxy_val = next((c["price"] for c in currencies if c["symbol"] == "DX-Y.NYB"), None)
        dxy_change = next((c["change"] for c in currencies if c["symbol"] == "DX-Y.NYB"), 0)
        btc_change = next((c["change"] for c in crypto if c["display"] == "BTC"), 0)

        # Derive risk-on/risk-off signal
        bullish_signals = 0
        total_signals = 5
        if vix.get("value") and vix["value"] < 20:
            bullish_signals += 1
        if fg.get("score", 50) > 50:
            bullish_signals += 1
        if sp500_change > 0:
            bullish_signals += 1
        if crude_change > -2:  # not crashing
            bullish_signals += 1
        if dxy_change <= 0:  # weak USD = bullish for EM
            bullish_signals += 1

        verdict = "RISK-ON" if bullish_signals >= 4 else "RISK-OFF" if bullish_signals <= 1 else "MIXED"

        return {
            "vix": vix.get("value"),
            "vix_status": vix.get("status", "UNKNOWN"),
            "vix_change": vix.get("change", 0),
            "fear_greed_score": fg.get("score", 50),
            "fear_greed_label": fg.get("label", "Neutral"),
            "sp500_change": sp500_change,
            "nifty_change": nifty_change,
            "crude_oil_change": crude_change,
            "brent_price": brent_price,
            "gold_change": gold_change,
            "usd_inr": usd_inr,
            "dxy": dxy_val,
            "dxy_change": dxy_change,
            "btc_change": btc_change,
            "global_verdict": verdict,
            "bullish_signals": bullish_signals,
            "total_signals": total_signals,
            "summary": (
                f"VIX {vix.get('value', '?')} ({vix.get('status', '?')}). "
                f"Fear & Greed: {fg.get('score', '?')} ({fg.get('label', '?')}). "
                f"S&P 500: {sp500_change:+.1f}%. "
                f"Crude Oil: {crude_change:+.1f}%. "
                f"Gold: {gold_change:+.1f}%. "
                f"USD/INR: {usd_inr or '?'}. "
                f"DXY: {dxy_change:+.1f}%. "
                f"BTC: {btc_change:+.1f}%. "
                f"Global verdict: {verdict}."
            ),
        }

    def bootstrap(self) -> None:
        """Pre-warm caches on startup. Call from lifespan()."""
        logger.info("Bootstrapping global market data...")
        try:
            self.get_global_indices()
            self.get_commodity_quotes()
            self.get_vix()
            self.get_fear_greed()
            self.get_crypto_quotes()
            self.get_currency_quotes()
            self.get_sector_performance()
            logger.info("Global market bootstrap complete")
        except Exception as e:
            logger.warning(f"Global market bootstrap partial failure: {e}")


def get_global_market_connector() -> GlobalMarketConnector:
    """Get singleton instance."""
    return GlobalMarketConnector.get_instance()
