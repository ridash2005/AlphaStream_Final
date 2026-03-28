"""
Financial market DuckDB schema for NLQ analytics.

Creates tables, loads Nifty 50 historical data, and builds pre-aggregated views.
"""

import csv
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import duckdb
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_DB_PATH: Optional[str] = None
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent  # backend/


def get_db_path() -> str:
    """Get the DuckDB database path from config."""
    global _DB_PATH
    if _DB_PATH is None:
        from src.config import get_settings
        settings = get_settings()
        db_path = settings.duckdb_path
        if not os.path.isabs(db_path):
            db_path = str(_BACKEND_ROOT / db_path)
        _DB_PATH = db_path
    return _DB_PATH


def get_connection(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Get a fresh DuckDB connection (DuckDB is not thread-safe)."""
    return duckdb.connect(get_db_path(), read_only=read_only)


# ── Schema DDL ─────────────────────────────────────────────────


def create_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Create all tables and views."""

    # Dimension: stocks
    con.execute("""
        CREATE TABLE IF NOT EXISTS dim_stocks (
            ticker       VARCHAR PRIMARY KEY,
            company_name VARCHAR,
            sector       VARCHAR,
            industry     VARCHAR,
            isin         VARCHAR,
            market_cap_cr DOUBLE DEFAULT 0,
            index_membership VARCHAR[] DEFAULT []
        )
    """)

    # Fact: daily prices
    con.execute("""
        CREATE TABLE IF NOT EXISTS fact_daily_prices (
            ticker VARCHAR,
            date   DATE,
            open   DOUBLE,
            high   DOUBLE,
            low    DOUBLE,
            close  DOUBLE,
            volume BIGINT,
            adj_close DOUBLE,
            PRIMARY KEY (ticker, date)
        )
    """)

    # Fact: signals
    con.execute("""
        CREATE TABLE IF NOT EXISTS fact_signals (
            signal_id    VARCHAR PRIMARY KEY,
            ticker       VARCHAR,
            signal_date  DATE,
            signal_type  VARCHAR,
            direction    VARCHAR,
            confidence   DOUBLE,
            alpha_score  DOUBLE DEFAULT 0,
            evidence_json JSON,
            backtest_json JSON,
            created_at   TIMESTAMP DEFAULT current_timestamp
        )
    """)

    # Fact: insider trades
    con.execute("""
        CREATE TABLE IF NOT EXISTS fact_insider_trades (
            id              VARCHAR PRIMARY KEY,
            ticker          VARCHAR,
            person_name     VARCHAR,
            person_category VARCHAR,
            trade_type      VARCHAR,
            quantity         BIGINT,
            value_lakhs     DOUBLE,
            trade_date      DATE,
            source          VARCHAR DEFAULT 'NSE'
        )
    """)

    # Fact: FII/DII flows
    con.execute("""
        CREATE TABLE IF NOT EXISTS fact_fii_dii_flows (
            date         DATE PRIMARY KEY,
            fii_buy_cr   DOUBLE,
            fii_sell_cr  DOUBLE,
            fii_net_cr   DOUBLE,
            dii_buy_cr   DOUBLE,
            dii_sell_cr  DOUBLE,
            dii_net_cr   DOUBLE
        )
    """)

    # Fact: corporate filings
    con.execute("""
        CREATE TABLE IF NOT EXISTS fact_filings (
            filing_id    VARCHAR PRIMARY KEY,
            ticker       VARCHAR,
            filing_date  TIMESTAMP,
            filing_type  VARCHAR,
            subject      TEXT,
            materiality  VARCHAR,
            sentiment    VARCHAR,
            key_facts    JSON,
            source_url   VARCHAR
        )
    """)

    # Fact: quarterly results
    con.execute("""
        CREATE TABLE IF NOT EXISTS fact_quarterly_results (
            ticker              VARCHAR,
            quarter             VARCHAR,
            revenue_cr          DOUBLE,
            pat_cr              DOUBLE,
            ebitda_margin       DOUBLE,
            yoy_revenue_growth  DOUBLE,
            yoy_pat_growth      DOUBLE,
            PRIMARY KEY (ticker, quarter)
        )
    """)

    # Fact: news articles (for NLQ querying)
    con.execute("""
        CREATE TABLE IF NOT EXISTS fact_articles (
            id          VARCHAR PRIMARY KEY,
            title       VARCHAR,
            description TEXT,
            content     TEXT,
            source      VARCHAR,
            url         VARCHAR,
            tickers     VARCHAR[],
            sentiment   VARCHAR,
            threat_level    VARCHAR DEFAULT 'info',
            threat_category VARCHAR DEFAULT 'general',
            threat_confidence DOUBLE DEFAULT 0.3,
            published_at TIMESTAMP,
            ingested_at  TIMESTAMP DEFAULT current_timestamp
        )
    """)

    # Insights table (for ambient alerts)
    con.execute("""
        CREATE TABLE IF NOT EXISTS insights (
            id         VARCHAR PRIMARY KEY,
            type       VARCHAR,
            severity   VARCHAR,
            title      VARCHAR,
            body       TEXT,
            ticker     VARCHAR,
            value      DOUBLE,
            threshold  DOUBLE,
            created_at TIMESTAMP DEFAULT current_timestamp,
            read       BOOLEAN DEFAULT false,
            dismissed  BOOLEAN DEFAULT false
        )
    """)

    # Migrate existing databases: add threat columns if missing
    _migrate_threat_columns(con)

    logger.info("DuckDB schema created")


def _migrate_threat_columns(con: duckdb.DuckDBPyConnection) -> None:
    """Add threat columns to fact_articles if they don't exist (migration)."""
    try:
        cols = [row[0] for row in con.execute("PRAGMA table_info('fact_articles')").fetchall()]
        if 'threat_level' not in cols:
            con.execute("ALTER TABLE fact_articles ADD COLUMN threat_level VARCHAR DEFAULT 'info'")
            con.execute("ALTER TABLE fact_articles ADD COLUMN threat_category VARCHAR DEFAULT 'general'")
            con.execute("ALTER TABLE fact_articles ADD COLUMN threat_confidence DOUBLE DEFAULT 0.3")
            logger.info("Migrated fact_articles: added threat_* columns")
    except Exception as e:
        logger.debug(f"Threat column migration: {e}")


# ── Views ──────────────────────────────────────────────────────


def create_views(con: duckdb.DuckDBPyConnection) -> None:
    """Create pre-aggregated views for NLQ querying."""

    con.execute("""
        CREATE OR REPLACE VIEW v_signal_summary AS
        SELECT
            s.ticker,
            d.company_name,
            d.sector,
            s.signal_date,
            s.signal_type,
            s.direction,
            s.confidence,
            s.alpha_score,
            s.evidence_json,
            s.backtest_json
        FROM fact_signals s
        LEFT JOIN dim_stocks d ON s.ticker = d.ticker
        ORDER BY s.signal_date DESC, s.alpha_score DESC
    """)

    con.execute("""
        CREATE OR REPLACE VIEW v_insider_activity_30d AS
        SELECT
            t.ticker,
            d.company_name,
            d.sector,
            t.person_name,
            t.person_category,
            t.trade_type,
            t.quantity,
            t.value_lakhs,
            t.trade_date
        FROM fact_insider_trades t
        LEFT JOIN dim_stocks d ON t.ticker = d.ticker
        WHERE t.trade_date >= current_date - INTERVAL '30 days'
        ORDER BY t.trade_date DESC
    """)

    con.execute("""
        CREATE OR REPLACE VIEW v_fii_dii_trend AS
        SELECT
            date,
            fii_buy_cr,
            fii_sell_cr,
            fii_net_cr,
            dii_buy_cr,
            dii_sell_cr,
            dii_net_cr,
            SUM(fii_net_cr) OVER (ORDER BY date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) AS fii_net_5d,
            SUM(dii_net_cr) OVER (ORDER BY date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) AS dii_net_5d,
            SUM(fii_net_cr) OVER (ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS fii_net_20d,
            SUM(dii_net_cr) OVER (ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS dii_net_20d
        FROM fact_fii_dii_flows
        ORDER BY date DESC
    """)

    con.execute("""
        CREATE OR REPLACE VIEW v_sector_heatmap AS
        SELECT
            d.sector,
            COUNT(DISTINCT d.ticker) AS stock_count,
            COUNT(DISTINCT s.signal_id) AS signal_count,
            AVG(s.alpha_score) AS avg_alpha_score,
            SUM(CASE WHEN s.direction = 'bullish' THEN 1 ELSE 0 END) AS bullish_count,
            SUM(CASE WHEN s.direction = 'bearish' THEN 1 ELSE 0 END) AS bearish_count
        FROM dim_stocks d
        LEFT JOIN fact_signals s ON d.ticker = s.ticker
            AND s.signal_date >= current_date - INTERVAL '7 days'
        GROUP BY d.sector
        ORDER BY avg_alpha_score DESC NULLS LAST
    """)

    con.execute("""
        CREATE OR REPLACE VIEW v_stock_screener AS
        SELECT
            d.ticker,
            d.company_name,
            d.sector,
            d.market_cap_cr,
            p.close AS last_close,
            p.volume AS last_volume,
            p.date AS last_date,
            latest_sig.signal_type AS latest_signal_type,
            latest_sig.direction AS latest_signal_dir,
            latest_sig.alpha_score AS latest_alpha_score
        FROM dim_stocks d
        LEFT JOIN (
            SELECT ticker, close, volume, date,
                   ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) AS rn
            FROM fact_daily_prices
        ) p ON d.ticker = p.ticker AND p.rn = 1
        LEFT JOIN (
            SELECT ticker, signal_type, direction, alpha_score,
                   ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY signal_date DESC) AS rn
            FROM fact_signals
        ) latest_sig ON d.ticker = latest_sig.ticker AND latest_sig.rn = 1
    """)

    con.execute("""
        CREATE OR REPLACE VIEW v_recent_news AS
        SELECT id, title, source, tickers, sentiment, published_at,
               LEFT(description, 200) AS summary
        FROM fact_articles
        ORDER BY published_at DESC
    """)

    logger.info("DuckDB views created")


# ── Data Loading ───────────────────────────────────────────────


def load_dim_stocks(con: duckdb.DuckDBPyConnection) -> int:
    """Load Nifty 50 stock dimensions from CSV."""
    csv_path = _BACKEND_ROOT / "data" / "nifty50_symbols.csv"
    if not csv_path.exists():
        logger.warning(f"Symbols CSV not found: {csv_path}")
        return 0

    count = con.execute("SELECT count(*) FROM dim_stocks").fetchone()[0]
    if count > 0:
        logger.info(f"dim_stocks already has {count} rows, skipping load")
        return count

    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            rows.append((
                r["ticker"],
                r["company_name"],
                r["sector"],
                r["industry"],
                r["isin"],
                0,
                ["nifty50"],
            ))

    con.executemany(
        "INSERT INTO dim_stocks VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    logger.info(f"Loaded {len(rows)} stocks into dim_stocks")
    return len(rows)


def load_historical_prices(con: duckdb.DuckDBPyConnection, period: str = "5y") -> int:
    """Load historical OHLCV data for all Nifty 50 stocks via yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        logger.warning("yfinance not installed, skipping price load")
        return 0

    # Check if already loaded
    existing = con.execute("SELECT count(*) FROM fact_daily_prices").fetchone()[0]
    if existing > 1000:
        logger.info(f"fact_daily_prices already has {existing} rows, skipping bulk load")
        return existing

    tickers = [r[0] for r in con.execute("SELECT ticker FROM dim_stocks").fetchall()]
    if not tickers:
        logger.warning("No tickers in dim_stocks, load those first")
        return 0

    ns_tickers = [f"{t}.NS" for t in tickers]
    total_loaded = 0

    # Download in batch for speed
    logger.info(f"Downloading {period} history for {len(ns_tickers)} tickers...")
    try:
        data = yf.download(ns_tickers, period=period, interval="1d", group_by="ticker", progress=False, threads=True)
    except Exception as e:
        logger.error(f"Batch download failed: {e}, trying individual")
        data = None

    for i, ticker in enumerate(tickers):
        ns = f"{ticker}.NS"
        try:
            if data is not None and ns in data.columns.get_level_values(0):
                hist = data[ns].dropna(subset=["Close"])
            else:
                tk = yf.Ticker(ns)
                hist = tk.history(period=period, interval="1d")

            if hist.empty:
                continue

            rows = []
            for date, row in hist.iterrows():
                dt = date.date() if hasattr(date, "date") else date
                rows.append((
                    ticker,
                    dt,
                    float(row.get("Open", 0)),
                    float(row.get("High", 0)),
                    float(row.get("Low", 0)),
                    float(row.get("Close", 0)),
                    int(row.get("Volume", 0)),
                    float(row.get("Close", 0)),  # adj_close
                ))

            if rows:
                con.executemany(
                    "INSERT OR IGNORE INTO fact_daily_prices VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    rows,
                )
                total_loaded += len(rows)

        except Exception as e:
            logger.warning(f"Failed to load {ticker}: {e}")
            continue

    logger.info(f"Loaded {total_loaded} price rows for {len(tickers)} tickers")
    return total_loaded


def seed_sample_signals(con: duckdb.DuckDBPyConnection) -> int:
    """Seed some sample signals for demo/testing."""
    existing = con.execute("SELECT count(*) FROM fact_signals").fetchone()[0]
    if existing > 0:
        return existing

    tickers = [r[0] for r in con.execute("SELECT ticker FROM dim_stocks LIMIT 15").fetchall()]
    if not tickers:
        return 0

    signal_types = ["technical", "filing", "insider", "flow", "sentiment"]
    directions = ["bullish", "bearish", "neutral"]
    patterns = ["rsi_divergence", "macd_crossover", "bollinger_breakout", "volume_breakout", "golden_cross"]

    rows = []
    np.random.seed(42)
    today = datetime.now().date()

    for ticker in tickers:
        n_signals = np.random.randint(1, 4)
        for _ in range(n_signals):
            sig_type = np.random.choice(signal_types)
            direction = np.random.choice(directions, p=[0.45, 0.35, 0.20])
            confidence = round(np.random.uniform(40, 95), 1)
            alpha_score = round(np.random.uniform(30, 90), 1)
            days_ago = np.random.randint(0, 7)

            evidence = {
                "pattern": np.random.choice(patterns) if sig_type == "technical" else sig_type,
                "detail": f"Sample {sig_type} signal for {ticker}",
            }

            rows.append((
                str(uuid.uuid4())[:8],
                ticker,
                today - timedelta(days=days_ago),
                sig_type,
                direction,
                confidence,
                alpha_score,
                json.dumps(evidence),
                json.dumps({"win_rate": round(np.random.uniform(0.5, 0.85), 2)}),
            ))

    con.executemany(
        "INSERT INTO fact_signals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, current_timestamp)",
        rows,
    )
    logger.info(f"Seeded {len(rows)} sample signals")
    return len(rows)


def seed_sample_fii_dii(con: duckdb.DuckDBPyConnection) -> int:
    """Seed sample FII/DII flow data for demo."""
    existing = con.execute("SELECT count(*) FROM fact_fii_dii_flows").fetchone()[0]
    if existing > 0:
        return existing

    np.random.seed(42)
    rows = []
    today = datetime.now().date()

    for i in range(60):
        dt = today - timedelta(days=i)
        if dt.weekday() >= 5:  # skip weekends
            continue
        fii_buy = round(np.random.uniform(5000, 15000), 2)
        fii_sell = round(np.random.uniform(5000, 15000), 2)
        dii_buy = round(np.random.uniform(4000, 12000), 2)
        dii_sell = round(np.random.uniform(4000, 12000), 2)
        rows.append((
            dt,
            fii_buy, fii_sell, round(fii_buy - fii_sell, 2),
            dii_buy, dii_sell, round(dii_buy - dii_sell, 2),
        ))

    con.executemany(
        "INSERT INTO fact_fii_dii_flows VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    logger.info(f"Seeded {len(rows)} FII/DII flow rows")
    return len(rows)


def seed_sample_insider_trades(con: duckdb.DuckDBPyConnection) -> int:
    """Seed sample insider trade data for demo."""
    existing = con.execute("SELECT count(*) FROM fact_insider_trades").fetchone()[0]
    if existing > 0:
        return existing

    np.random.seed(42)
    tickers = [r[0] for r in con.execute("SELECT ticker FROM dim_stocks LIMIT 10").fetchall()]
    categories = ["promoter", "director", "kmp"]
    names = ["Mukesh Ambani", "N Chandrasekaran", "Salil Parekh", "Sashidhar Jagdishan", "Sandeep Bakhshi"]

    rows = []
    today = datetime.now().date()

    for ticker in tickers:
        n_trades = np.random.randint(0, 3)
        for _ in range(n_trades):
            trade_type = np.random.choice(["buy", "sell"], p=[0.6, 0.4])
            qty = int(np.random.uniform(1000, 500000))
            value = round(qty * np.random.uniform(50, 3000) / 1e5, 2)
            days_ago = np.random.randint(1, 30)
            rows.append((
                str(uuid.uuid4())[:8],
                ticker,
                np.random.choice(names),
                np.random.choice(categories),
                trade_type,
                qty,
                value,
                today - timedelta(days=days_ago),
                "NSE",
            ))

    if rows:
        con.executemany(
            "INSERT INTO fact_insider_trades VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
    logger.info(f"Seeded {len(rows)} insider trade rows")
    return len(rows)


# ── Main Init ──────────────────────────────────────────────────


def init_database(load_prices: bool = True, price_period: str = "5y") -> dict:
    """
    Initialize the full market analytics database.

    Returns dict with row counts for each table.
    """
    con = get_connection()
    try:
        create_schema(con)
        stocks = load_dim_stocks(con)
        create_views(con)

        prices = 0
        if load_prices:
            prices = load_historical_prices(con, period=price_period)

        signals = seed_sample_signals(con)
        fii_dii = seed_sample_fii_dii(con)
        insider = seed_sample_insider_trades(con)

        # Recreate views after data load
        create_views(con)

        result = {
            "dim_stocks": stocks,
            "fact_daily_prices": prices,
            "fact_signals": signals,
            "fact_fii_dii_flows": fii_dii,
            "fact_insider_trades": insider,
        }
        logger.info(f"Database initialized: {result}")
        return result
    finally:
        con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = init_database(load_prices=True, price_period="1y")
    print(f"\nDatabase initialized: {result}")

    # Quick verification
    con = get_connection(read_only=True)
    print("\n--- Verification ---")
    print(f"dim_stocks: {con.execute('SELECT count(*) FROM dim_stocks').fetchone()[0]} rows")
    print(f"fact_daily_prices: {con.execute('SELECT count(*) FROM fact_daily_prices').fetchone()[0]} rows")
    print(f"fact_signals: {con.execute('SELECT count(*) FROM fact_signals').fetchone()[0]} rows")
    print(f"fact_fii_dii_flows: {con.execute('SELECT count(*) FROM fact_fii_dii_flows').fetchone()[0]} rows")
    print(f"fact_insider_trades: {con.execute('SELECT count(*) FROM fact_insider_trades').fetchone()[0]} rows")

    print("\n--- Sample: v_stock_screener ---")
    df = con.execute("SELECT * FROM v_stock_screener LIMIT 5").fetchdf()
    print(df.to_string())

    print("\n--- Sample: v_signal_summary ---")
    df = con.execute("SELECT ticker, signal_type, direction, alpha_score FROM v_signal_summary LIMIT 5").fetchdf()
    print(df.to_string())
    con.close()
