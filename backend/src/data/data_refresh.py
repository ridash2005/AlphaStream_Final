"""
Central Data Refresh Service.

On startup + every 30min:
1. Cache 1yr price data
2. Run pattern detection -> write real signals
3. Fetch live FII/DII -> write flows
4. Fetch live insider trades -> write trades
5. Fetch RSS articles -> write to DuckDB
6. Fetch bulk/block deals -> write deals + signals
"""
import asyncio
import logging
import time
import uuid
from datetime import datetime

from src.data.market_schema import get_connection, create_schema, create_views, load_dim_stocks

logger = logging.getLogger(__name__)

_scheduler_task = None


def run_full_refresh(load_prices: bool = True, run_signals: bool = True) -> dict:
    """Run complete data refresh. Returns counts."""
    results = {}
    start = time.time()

    # 0. Ensure schema + dim_stocks
    con = get_connection()
    create_schema(con)
    load_dim_stocks(con)
    create_views(con)
    con.close()

    # 1. Cache prices (1yr)
    if load_prices:
        results["prices"] = _refresh_prices()

    # 2. Run pattern detection on all stocks -> real signals
    if run_signals:
        results["signals"] = _refresh_signals()

    # 3. Fetch live FII/DII
    results["fii_dii"] = _refresh_fii_dii()

    # 4. Fetch live insider trades
    results["insider"] = _refresh_insider_trades()

    # 5. Fetch RSS articles
    results["articles"] = _refresh_articles()

    # 6. Update Groww live prices for dim_stocks market_cap
    results["groww_refresh"] = _refresh_groww_data()

    # 7. Refresh global market data (WorldMonitor-sourced)
    results["global_market"] = _refresh_global_market()

    # 8. Fetch bulk/block deals from NSE
    results["bulk_block_deals"] = _refresh_bulk_block_deals()

    # 9. Regenerate views
    con = get_connection()
    create_views(con)
    con.close()

    elapsed = time.time() - start
    results["elapsed_seconds"] = round(elapsed, 1)
    logger.info(f"Data refresh complete in {elapsed:.1f}s: {results}")
    return results


def _refresh_prices() -> int:
    """Load/update price cache."""
    try:
        from src.data.market_schema import load_historical_prices, get_connection
        con = get_connection()
        count = load_historical_prices(con, period="1y")
        con.close()
        return count
    except Exception as e:
        logger.warning(f"Price refresh failed: {e}")
        return 0


def _refresh_signals() -> int:
    """Run PatternAgent on all stocks, write real signals to DuckDB."""
    try:
        from src.data.ticker_universe import get_all_tickers
        from src.agents.pattern_agent import PatternAgent
        from src.data.signal_writer import write_signal

        pa = PatternAgent()
        tickers = get_all_tickers()
        count = 0

        for ticker in tickers:
            try:
                patterns = pa.detect_all(ticker, period="6mo")
                for p in patterns:
                    written = write_signal(
                        ticker=ticker,
                        signal_type="technical",
                        direction=p.get("direction", "neutral"),
                        confidence=p.get("confidence", 0.5) * 100,
                        evidence=p,
                    )
                    if written:
                        count += 1
            except Exception:
                continue

        logger.info(f"Signal refresh: {count} new signals from {len(tickers)} stocks")
        return count
    except Exception as e:
        logger.warning(f"Signal refresh failed: {e}")
        return 0


def _refresh_fii_dii() -> int:
    """Fetch live FII/DII data from NSE."""
    try:
        from src.connectors.nse_connector import get_nse_connector
        from src.data.signal_writer import write_fii_dii

        nse = get_nse_connector()
        data = nse.get_fii_dii_data()
        if not data:
            return 0

        count = 0
        # NSE returns current day data
        if isinstance(data, list):
            for entry in data:
                date = entry.get("date", datetime.now().strftime("%Y-%m-%d"))
                written = write_fii_dii(
                    date, entry.get("fii_buy", 0), entry.get("fii_sell", 0),
                    entry.get("dii_buy", 0), entry.get("dii_sell", 0),
                )
                if written:
                    count += 1
        elif isinstance(data, dict):
            date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
            written = write_fii_dii(
                date, data.get("fii_buy", 0), data.get("fii_sell", 0),
                data.get("dii_buy", 0), data.get("dii_sell", 0),
            )
            if written:
                count = 1

        return count
    except Exception as e:
        logger.warning(f"FII/DII refresh failed: {e}")
        return 0


def _refresh_insider_trades() -> int:
    """Fetch live insider trades from NSE."""
    try:
        from src.connectors.insider_connector import get_insider_connector
        from src.data.signal_writer import write_insider_trade

        ic = get_insider_connector()
        trades = ic.get_pit_data(days=30)
        count = sum(1 for t in trades if write_insider_trade(t))
        return count
    except Exception as e:
        logger.warning(f"Insider refresh failed: {e}")
        return 0


def _refresh_articles() -> int:
    """Fetch RSS articles and ingest to DuckDB."""
    try:
        from src.data.article_ingest import ingest_rss_to_duckdb
        return ingest_rss_to_duckdb()
    except Exception as e:
        logger.warning(f"Article refresh failed: {e}")
        return 0


def _refresh_global_market() -> int:
    """Refresh global market data (indices, commodities, VIX, Fear & Greed)."""
    try:
        from src.connectors.global_market_connector import get_global_market_connector
        gmc = get_global_market_connector()
        gmc.bootstrap()
        return 1
    except Exception as e:
        logger.warning(f"Global market refresh failed: {e}")
        return 0


def _refresh_groww_data() -> int:
    """Refresh stock data from Groww API (live prices, 52w range)."""
    try:
        from src.data.ticker_universe import refresh_dim_stocks
        return refresh_dim_stocks()
    except Exception as e:
        logger.warning(f"Groww refresh failed: {e}")
        return 0


def _refresh_bulk_block_deals() -> int:
    """Fetch bulk and block deals from NSE, ingest into fact_bulk_deals and generate signals."""
    try:
        from src.connectors.nse_connector import get_nse_connector
        from src.data.market_schema import get_connection
        from src.data.signal_writer import write_signal

        nse = get_nse_connector()
        bulk_deals = nse.get_bulk_deals(days=7)
        block_deals = nse.get_block_deals(days=7)

        con = get_connection()
        count = 0

        try:
            for deal_type, deals in [("bulk", bulk_deals), ("block", block_deals)]:
                for deal in deals:
                    ticker = deal.get("symbol", deal.get("ticker", ""))
                    trade_date = deal.get("date", deal.get("dealDate", ""))
                    quantity = int(deal.get("quantity", deal.get("qty", 0)) or 0)
                    price = float(deal.get("price", deal.get("avgPrice", 0)) or 0)
                    value_cr = float(deal.get("value_cr", 0) or 0)
                    if value_cr == 0 and quantity and price:
                        value_cr = round((quantity * price) / 1e7, 2)
                    client_name = deal.get("clientName", deal.get("client", ""))

                    try:
                        con.execute("""
                            INSERT INTO fact_bulk_deals
                                (id, trade_date, ticker, deal_type, quantity, price, value_cr, client_name)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, [
                            str(uuid.uuid4())[:8],
                            trade_date,
                            ticker,
                            deal_type,
                            quantity,
                            price,
                            value_cr,
                            client_name,
                        ])
                        count += 1
                    except Exception as e:
                        logger.debug(f"Bulk deal insert failed: {e}")
                        continue

                    # Generate signal for large deals (> 50 Cr)
                    if value_cr > 50:
                        alpha = min(value_cr / 10, 100)
                        write_signal(
                            ticker=ticker,
                            signal_type=f"{deal_type}_deal",
                            direction="bullish",
                            confidence=70,
                            alpha_score=alpha,
                            evidence={
                                "pattern": f"{deal_type}_deal",
                                "detail": f"Large {deal_type} deal: {value_cr} Cr at Rs {price}",
                                "client": client_name,
                                "quantity": quantity,
                            },
                        )
        finally:
            con.close()

        logger.info(f"Bulk/block deal refresh: {count} deals ingested")
        return count
    except Exception as e:
        logger.warning(f"Bulk/block deal refresh failed: {e}")
        return 0


async def _background_refresh_loop(interval_minutes: int = 30):
    """Background task for periodic data refresh."""
    while True:
        await asyncio.sleep(interval_minutes * 60)
        try:
            results = run_full_refresh(load_prices=False, run_signals=True)
            logger.info(f"Background refresh: {results}")
        except Exception as e:
            logger.error(f"Background refresh failed: {e}")


def start_background_refresh(interval_minutes: int = 30):
    """Start background data refresh scheduler."""
    global _scheduler_task
    if _scheduler_task is None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        _scheduler_task = loop.create_task(_background_refresh_loop(interval_minutes))
        logger.info(f"Data refresh scheduler started (every {interval_minutes} min)")
