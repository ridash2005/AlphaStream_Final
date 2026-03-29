"""
Financial market DuckDB schema for NLQ analytics.

Creates tables, loads Nifty 200 historical data, and builds pre-aggregated views.
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

    # Fact: bulk and block deals
    con.execute("""
        CREATE TABLE IF NOT EXISTS fact_bulk_deals (
            id VARCHAR DEFAULT gen_random_uuid()::VARCHAR,
            trade_date DATE,
            ticker VARCHAR,
            deal_type VARCHAR,
            quantity BIGINT,
            price DECIMAL(12,2),
            value_cr DECIMAL(12,2),
            client_name VARCHAR,
            created_at TIMESTAMP DEFAULT now()
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


def _seed_nifty200_stocks(con: duckdb.DuckDBPyConnection) -> int:
    """
    Seed Nifty Next 50 + Nifty Midcap 100 stocks into dim_stocks.

    Uses INSERT OR IGNORE so rows already loaded from CSV are untouched.
    Covers roughly 150 additional tickers beyond Nifty 50.
    """
    # (ticker, company_name, sector, industry, isin, market_cap_cr, index_membership)
    extra_stocks = [
        # -- IT --
        ("MPHASIS", "Mphasis Ltd", "Information Technology", "IT Services & Consulting", "INE356A01018", 48000, ["nifty_next50"]),
        ("COFORGE", "Coforge Ltd", "Information Technology", "IT Services & Consulting", "INE591G01017", 36000, ["nifty_midcap100"]),
        ("PERSISTENT", "Persistent Systems Ltd", "Information Technology", "IT Services & Consulting", "INE262H01013", 52000, ["nifty_midcap100"]),
        ("LTTS", "L&T Technology Services Ltd", "Information Technology", "IT Services & Consulting", "INE010V01017", 42000, ["nifty_midcap100"]),
        ("TATAELXSI", "Tata Elxsi Ltd", "Information Technology", "IT Services & Consulting", "INE670A01012", 34000, ["nifty_midcap100"]),
        # -- Banking / NBFC --
        ("BANKBARODA", "Bank of Baroda", "Financial Services", "Banks", "INE028A01039", 120000, ["nifty_next50"]),
        ("PNB", "Punjab National Bank", "Financial Services", "Banks", "INE160A01022", 95000, ["nifty_next50"]),
        ("CANBK", "Canara Bank", "Financial Services", "Banks", "INE476A01014", 90000, ["nifty_next50"]),
        ("IDFCFIRSTB", "IDFC First Bank Ltd", "Financial Services", "Banks", "INE092T01019", 48000, ["nifty_midcap100"]),
        ("AUBANK", "AU Small Finance Bank Ltd", "Financial Services", "Banks", "INE949L01017", 45000, ["nifty_midcap100"]),
        ("BANDHANBNK", "Bandhan Bank Ltd", "Financial Services", "Banks", "INE545U01014", 30000, ["nifty_midcap100"]),
        ("FEDERALBNK", "Federal Bank Ltd", "Financial Services", "Banks", "INE171A01029", 35000, ["nifty_midcap100"]),
        ("CHOLAFIN", "Cholamandalam Investment and Finance Co Ltd", "Financial Services", "Consumer Finance", "INE121A01024", 85000, ["nifty_next50"]),
        ("MUTHOOTFIN", "Muthoot Finance Ltd", "Financial Services", "Consumer Finance", "INE414G01012", 55000, ["nifty_midcap100"]),
        ("MANAPPURAM", "Manappuram Finance Ltd", "Financial Services", "Consumer Finance", "INE522D01027", 18000, ["nifty_midcap100"]),
        ("PFC", "Power Finance Corporation Ltd", "Financial Services", "Term Lending", "INE134E01011", 130000, ["nifty_next50"]),
        ("RECLTD", "REC Ltd", "Financial Services", "Term Lending", "INE020B01018", 115000, ["nifty_next50"]),
        ("LICHSGFIN", "LIC Housing Finance Ltd", "Financial Services", "Housing Finance", "INE115A01026", 35000, ["nifty_midcap100"]),
        ("CANFINHOME", "Can Fin Homes Ltd", "Financial Services", "Housing Finance", "INE477A01020", 10000, ["nifty_midcap100"]),
        # -- Auto --
        ("ASHOKLEY", "Ashok Leyland Ltd", "Automobile", "Commercial Vehicles", "INE208A01029", 55000, ["nifty_next50"]),
        ("TVSMOTOR", "TVS Motor Company Ltd", "Automobile", "Two Wheelers", "INE494B01023", 80000, ["nifty_next50"]),
        ("MOTHERSON", "Samvardhana Motherson International Ltd", "Automobile", "Auto Components", "INE775A01035", 72000, ["nifty_next50"]),
        ("BALKRISIND", "Balkrishna Industries Ltd", "Automobile", "Tyres", "INE787D01026", 45000, ["nifty_midcap100"]),
        ("MRF", "MRF Ltd", "Automobile", "Tyres", "INE883A01011", 55000, ["nifty_midcap100"]),
        ("BHARATFORG", "Bharat Forge Ltd", "Automobile", "Auto Components", "INE465A01025", 45000, ["nifty_midcap100"]),
        ("EXIDEIND", "Exide Industries Ltd", "Automobile", "Auto Components", "INE302A01020", 25000, ["nifty_midcap100"]),
        ("AMARAJABAT", "Amara Raja Energy & Mobility Ltd", "Automobile", "Auto Components", "INE885A01032", 18000, ["nifty_midcap100"]),
        # -- Pharma / Healthcare --
        ("AUROPHARMA", "Aurobindo Pharma Ltd", "Healthcare", "Pharmaceuticals", "INE406A01037", 60000, ["nifty_next50"]),
        ("LUPIN", "Lupin Ltd", "Healthcare", "Pharmaceuticals", "INE326A01037", 70000, ["nifty_next50"]),
        ("BIOCON", "Biocon Ltd", "Healthcare", "Biotechnology", "INE376G01013", 32000, ["nifty_midcap100"]),
        ("TORNTPHARM", "Torrent Pharmaceuticals Ltd", "Healthcare", "Pharmaceuticals", "INE685A01028", 65000, ["nifty_midcap100"]),
        ("ALKEM", "Alkem Laboratories Ltd", "Healthcare", "Pharmaceuticals", "INE540L01014", 50000, ["nifty_midcap100"]),
        ("IPCALAB", "IPCA Laboratories Ltd", "Healthcare", "Pharmaceuticals", "INE571A01020", 28000, ["nifty_midcap100"]),
        ("MAXHEALTH", "Max Healthcare Institute Ltd", "Healthcare", "Hospitals & Diagnostics", "INE027H01010", 70000, ["nifty_next50"]),
        ("FORTIS", "Fortis Healthcare Ltd", "Healthcare", "Hospitals & Diagnostics", "INE061F01013", 28000, ["nifty_midcap100"]),
        ("LALPATHLAB", "Dr Lal PathLabs Ltd", "Healthcare", "Diagnostics", "INE600L01024", 22000, ["nifty_midcap100"]),
        ("METROPOLIS", "Metropolis Healthcare Ltd", "Healthcare", "Diagnostics", "INE112L01030", 14000, ["nifty_midcap100"]),
        ("GLENMARK", "Glenmark Pharmaceuticals Ltd", "Healthcare", "Pharmaceuticals", "INE935A01035", 16000, ["nifty_midcap100"]),
        ("NATCOPHARMA", "Natco Pharma Ltd", "Healthcare", "Pharmaceuticals", "INE987B01026", 18000, ["nifty_midcap100"]),
        # -- FMCG --
        ("DABUR", "Dabur India Ltd", "Fast Moving Consumer Goods", "FMCG", "INE016A01026", 88000, ["nifty_next50"]),
        ("GODREJCP", "Godrej Consumer Products Ltd", "Fast Moving Consumer Goods", "FMCG", "INE102D01028", 95000, ["nifty_next50"]),
        ("MARICO", "Marico Ltd", "Fast Moving Consumer Goods", "FMCG", "INE196A01026", 70000, ["nifty_next50"]),
        ("COLPAL", "Colgate-Palmolive (India) Ltd", "Fast Moving Consumer Goods", "FMCG", "INE259A01022", 58000, ["nifty_midcap100"]),
        ("VBL", "Varun Beverages Ltd", "Fast Moving Consumer Goods", "Beverages", "INE200M01013", 155000, ["nifty_next50"]),
        ("UNITDSPR", "United Spirits Ltd", "Fast Moving Consumer Goods", "Alcoholic Beverages", "INE854D01024", 62000, ["nifty_midcap100"]),
        ("EMAMILTD", "Emami Ltd", "Fast Moving Consumer Goods", "FMCG", "INE548C01032", 18000, ["nifty_midcap100"]),
        ("JUBLFOOD", "Jubilant FoodWorks Ltd", "Fast Moving Consumer Goods", "Quick Service Restaurants", "INE797F01012", 35000, ["nifty_midcap100"]),
        # -- Energy / Oil / Utilities --
        ("GAIL", "GAIL (India) Ltd", "Energy", "Gas Transmission", "INE129A01019", 120000, ["nifty_next50"]),
        ("PETRONET", "Petronet LNG Ltd", "Energy", "Gas Transmission", "INE347G01014", 45000, ["nifty_midcap100"]),
        ("TATAPOWER", "Tata Power Company Ltd", "Utilities", "Power Generation", "INE245A01021", 110000, ["nifty_next50"]),
        ("ADANIGREEN", "Adani Green Energy Ltd", "Utilities", "Renewable Energy", "INE364U01010", 160000, ["nifty_next50"]),
        ("IOC", "Indian Oil Corporation Ltd", "Energy", "Petroleum Products", "INE242A01010", 180000, ["nifty_next50"]),
        ("HINDPETRO", "Hindustan Petroleum Corporation Ltd", "Energy", "Petroleum Products", "INE094A01015", 60000, ["nifty_midcap100"]),
        ("IGL", "Indraprastha Gas Ltd", "Energy", "City Gas Distribution", "INE203G01027", 28000, ["nifty_midcap100"]),
        ("MGL", "Mahanagar Gas Ltd", "Energy", "City Gas Distribution", "INE002S01010", 14000, ["nifty_midcap100"]),
        ("NHPC", "NHPC Ltd", "Utilities", "Power Generation", "INE848E01016", 70000, ["nifty_midcap100"]),
        ("SJVN", "SJVN Ltd", "Utilities", "Power Generation", "INE002L01015", 45000, ["nifty_midcap100"]),
        ("ADANIPOWER", "Adani Power Ltd", "Utilities", "Power Generation", "INE814H01011", 175000, ["nifty_midcap100"]),
        ("TORNTPOWER", "Torrent Power Ltd", "Utilities", "Power Generation", "INE813H01021", 55000, ["nifty_midcap100"]),
        ("CESC", "CESC Ltd", "Utilities", "Power Distribution", "INE486A01013", 14000, ["nifty_midcap100"]),
        # -- Metals / Mining --
        ("VEDL", "Vedanta Ltd", "Materials", "Mining & Metals", "INE205A01025", 160000, ["nifty_next50"]),
        ("NMDC", "NMDC Ltd", "Materials", "Mining", "INE584A01023", 62000, ["nifty_midcap100"]),
        ("JINDALSTEL", "Jindal Steel & Power Ltd", "Materials", "Iron & Steel", "INE749A01030", 78000, ["nifty_next50"]),
        ("NATIONALUM", "National Aluminium Company Ltd", "Materials", "Aluminium", "INE139A01034", 28000, ["nifty_midcap100"]),
        ("SAIL", "Steel Authority of India Ltd", "Materials", "Iron & Steel", "INE114A01011", 45000, ["nifty_midcap100"]),
        ("JSWENERGY", "JSW Energy Ltd", "Utilities", "Power Generation", "INE121E01018", 72000, ["nifty_midcap100"]),
        ("APLAPOLLO", "APL Apollo Tubes Ltd", "Materials", "Iron & Steel", "INE702C01019", 30000, ["nifty_midcap100"]),
        # -- Telecom --
        ("IDEA", "Vodafone Idea Ltd", "Communication Services", "Telecom Services", "INE669E01016", 55000, ["nifty_midcap100"]),
        # -- Infrastructure / Construction / Real Estate --
        ("DLF", "DLF Ltd", "Real Estate", "Real Estate Development", "INE271C01023", 130000, ["nifty_next50"]),
        ("GODREJPROP", "Godrej Properties Ltd", "Real Estate", "Real Estate Development", "INE484J01027", 55000, ["nifty_midcap100"]),
        ("OBEROIRLTY", "Oberoi Realty Ltd", "Real Estate", "Real Estate Development", "INE093I01010", 50000, ["nifty_midcap100"]),
        ("PRESTIGE", "Prestige Estates Projects Ltd", "Real Estate", "Real Estate Development", "INE811K01011", 35000, ["nifty_midcap100"]),
        ("PHOENIXLTD", "The Phoenix Mills Ltd", "Real Estate", "Real Estate Management", "INE211B01039", 38000, ["nifty_midcap100"]),
        ("BRIGADE", "Brigade Enterprises Ltd", "Real Estate", "Real Estate Development", "INE791I01019", 15000, ["nifty_midcap100"]),
        ("LODHA", "Macrotech Developers Ltd", "Real Estate", "Real Estate Development", "INE670K01029", 80000, ["nifty_next50"]),
        ("IRCON", "Ircon International Ltd", "Industrials", "Construction & Engineering", "INE962Y01021", 18000, ["nifty_midcap100"]),
        ("NCC", "NCC Ltd", "Industrials", "Construction & Engineering", "INE868B01028", 12000, ["nifty_midcap100"]),
        ("KEC", "KEC International Ltd", "Industrials", "Capital Goods", "INE389H01022", 16000, ["nifty_midcap100"]),
        # -- Chemicals --
        ("PIDILITIND", "Pidilite Industries Ltd", "Materials", "Specialty Chemicals", "INE318A01026", 130000, ["nifty_next50"]),
        ("SRF", "SRF Ltd", "Materials", "Specialty Chemicals", "INE647A01010", 65000, ["nifty_midcap100"]),
        ("AARTI", "Aarti Industries Ltd", "Materials", "Specialty Chemicals", "INE769A01020", 20000, ["nifty_midcap100"]),
        ("DEEPAKNTR", "Deepak Nitrite Ltd", "Materials", "Specialty Chemicals", "INE288B01029", 25000, ["nifty_midcap100"]),
        ("CLEAN", "Clean Science and Technology Ltd", "Materials", "Specialty Chemicals", "INE209S01016", 14000, ["nifty_midcap100"]),
        ("ATUL", "Atul Ltd", "Materials", "Specialty Chemicals", "INE100A01010", 18000, ["nifty_midcap100"]),
        ("NAVINFLUOR", "Navin Fluorine International Ltd", "Materials", "Specialty Chemicals", "INE048G01026", 14000, ["nifty_midcap100"]),
        ("FLUOROCHEM", "Gujarat Fluorochemicals Ltd", "Materials", "Specialty Chemicals", "INE386A01016", 20000, ["nifty_midcap100"]),
        # -- Insurance --
        ("ICICIPRULI", "ICICI Prudential Life Insurance Co Ltd", "Financial Services", "Life Insurance", "INE726G01019", 80000, ["nifty_next50"]),
        ("STARHEALTH", "Star Health and Allied Insurance Co Ltd", "Financial Services", "General Insurance", "INE575P01011", 35000, ["nifty_midcap100"]),
        ("NIACL", "New India Assurance Company Ltd", "Financial Services", "General Insurance", "INE470Y01017", 22000, ["nifty_midcap100"]),
        ("ICICIGI", "ICICI Lombard General Insurance Co Ltd", "Financial Services", "General Insurance", "INE765G01017", 62000, ["nifty_midcap100"]),
        # -- Consumer / Retail / New-age --
        ("ZOMATO", "Zomato Ltd", "Consumer Services", "Internet & Catalogue Retail", "INE758T01015", 155000, ["nifty_next50"]),
        ("PAYTM", "One97 Communications Ltd", "Information Technology", "Fintech", "INE982J01020", 28000, ["nifty_midcap100"]),
        ("NYKAA", "FSN E-Commerce Ventures Ltd", "Consumer Services", "E-Commerce", "INE388Y01029", 25000, ["nifty_midcap100"]),
        ("DMART", "Avenue Supermarts Ltd", "Consumer Services", "Retail", "INE192R01011", 270000, ["nifty_next50"]),
        ("TRENT", "Trent Ltd", "Consumer Services", "Retail", "INE849A01020", 165000, ["nifty_next50"]),
        ("PAGEIND", "Page Industries Ltd", "Consumer Durables", "Apparel", "INE761H01022", 42000, ["nifty_midcap100"]),
        ("RELAXO", "Relaxo Footwears Ltd", "Consumer Durables", "Footwear", "INE131B01039", 15000, ["nifty_midcap100"]),
        ("POLYCAB", "Polycab India Ltd", "Consumer Durables", "Electrical Equipment", "INE455K01017", 70000, ["nifty_next50"]),
        ("CROMPTON", "Crompton Greaves Consumer Electricals Ltd", "Consumer Durables", "Electrical Equipment", "INE299U01018", 22000, ["nifty_midcap100"]),
        ("VOLTAS", "Voltas Ltd", "Consumer Durables", "Consumer Electronics", "INE226A01021", 30000, ["nifty_midcap100"]),
        ("BATAINDIA", "Bata India Ltd", "Consumer Durables", "Footwear", "INE176A01028", 22000, ["nifty_midcap100"]),
        ("WHIRLPOOL", "Whirlpool of India Ltd", "Consumer Durables", "Consumer Electronics", "INE716A01013", 14000, ["nifty_midcap100"]),
        # -- Defence / PSU --
        ("HAL", "Hindustan Aeronautics Ltd", "Industrials", "Aerospace & Defence", "INE066F01020", 260000, ["nifty_next50"]),
        ("BEL", "Bharat Electronics Ltd", "Industrials", "Aerospace & Defence", "INE263A01024", 145000, ["nifty_next50"]),
        ("IRCTC", "Indian Railway Catering and Tourism Corporation Ltd", "Consumer Services", "Travel & Tourism", "INE335Y01020", 62000, ["nifty_midcap100"]),
        ("CONCOR", "Container Corporation of India Ltd", "Industrials", "Logistics", "INE111A01025", 42000, ["nifty_midcap100"]),
        ("IRFC", "Indian Railway Finance Corporation Ltd", "Financial Services", "Term Lending", "INE053F01010", 160000, ["nifty_midcap100"]),
        ("HUDCO", "Housing & Urban Development Corporation Ltd", "Financial Services", "Housing Finance", "INE031A01017", 38000, ["nifty_midcap100"]),
        ("BDL", "Bharat Dynamics Ltd", "Industrials", "Aerospace & Defence", "INE171Z01018", 32000, ["nifty_midcap100"]),
        ("COCHINSHIP", "Cochin Shipyard Ltd", "Industrials", "Shipbuilding", "INE704P01017", 30000, ["nifty_midcap100"]),
        # -- Cement --
        ("AMBUJACEM", "Ambuja Cements Ltd", "Construction Materials", "Cement", "INE079A01024", 120000, ["nifty_next50"]),
        ("ACC", "ACC Ltd", "Construction Materials", "Cement", "INE012A01025", 45000, ["nifty_midcap100"]),
        ("SHREECEM", "Shree Cement Ltd", "Construction Materials", "Cement", "INE070A01015", 90000, ["nifty_next50"]),
        ("RAMCOCEM", "The Ramco Cements Ltd", "Construction Materials", "Cement", "INE331A01037", 20000, ["nifty_midcap100"]),
        ("DALMIACEM", "Dalmia Bharat Ltd", "Construction Materials", "Cement", "INE439L01019", 28000, ["nifty_midcap100"]),
        ("JKCEMENT", "JK Cement Ltd", "Construction Materials", "Cement", "INE823G01014", 22000, ["nifty_midcap100"]),
        ("STARCEMENT", "Star Cement Ltd", "Construction Materials", "Cement", "INE460H01021", 5000, ["nifty_midcap100"]),
        # -- Capital Goods / Engineering --
        ("SIEMENS", "Siemens Ltd", "Industrials", "Capital Goods", "INE003A01024", 175000, ["nifty_next50"]),
        ("ABB", "ABB India Ltd", "Industrials", "Capital Goods", "INE117A01022", 130000, ["nifty_next50"]),
        ("HAVELLS", "Havells India Ltd", "Consumer Durables", "Electrical Equipment", "INE176B01034", 95000, ["nifty_next50"]),
        ("CUMMINSIND", "Cummins India Ltd", "Industrials", "Capital Goods", "INE298A01020", 68000, ["nifty_midcap100"]),
        ("THERMAX", "Thermax Ltd", "Industrials", "Capital Goods", "INE152A01029", 30000, ["nifty_midcap100"]),
        ("GRINFRA", "G R Infraprojects Ltd", "Industrials", "Construction & Engineering", "INE201P01038", 8000, ["nifty_midcap100"]),
        ("KALYANKJIL", "Kalyan Jewellers India Ltd", "Consumer Durables", "Precious Metals & Jewellery", "INE303R01014", 38000, ["nifty_midcap100"]),
        # -- Miscellaneous / Diversified --
        ("PIIND", "PI Industries Ltd", "Materials", "Agrochemicals", "INE603J01030", 45000, ["nifty_midcap100"]),
        ("UPL", "UPL Ltd", "Materials", "Agrochemicals", "INE628A01036", 35000, ["nifty_midcap100"]),
        ("COROMANDEL", "Coromandel International Ltd", "Materials", "Fertilizers", "INE169A01031", 38000, ["nifty_midcap100"]),
        ("DEEPAKFERT", "Deepak Fertilisers and Petrochemicals Corp Ltd", "Materials", "Fertilizers", "INE501A01019", 8000, ["nifty_midcap100"]),
        ("MCDOWELL-N", "United Breweries Ltd", "Fast Moving Consumer Goods", "Alcoholic Beverages", "INE686F01025", 40000, ["nifty_midcap100"]),
        ("INDIGO", "InterGlobe Aviation Ltd", "Consumer Services", "Airlines", "INE646L01027", 85000, ["nifty_next50"]),
        ("HONAUT", "Honeywell Automation India Ltd", "Industrials", "Capital Goods", "INE671A01010", 40000, ["nifty_midcap100"]),
        ("KAYNES", "Kaynes Technology India Ltd", "Information Technology", "Electronics", "INE918Z01010", 18000, ["nifty_midcap100"]),
        ("SONACOMS", "Sona BLW Precision Forgings Ltd", "Automobile", "Auto Components", "INE073K01018", 32000, ["nifty_midcap100"]),
        ("SUNTV", "Sun TV Network Ltd", "Communication Services", "Media & Entertainment", "INE424H01027", 25000, ["nifty_midcap100"]),
        ("PVRINOX", "PVR INOX Ltd", "Consumer Services", "Media & Entertainment", "INE191H01014", 12000, ["nifty_midcap100"]),
        ("CAMS", "Computer Age Management Services Ltd", "Financial Services", "Asset Management", "INE596I01012", 14000, ["nifty_midcap100"]),
        ("CDSL", "Central Depository Services (India) Ltd", "Financial Services", "Capital Markets", "INE736A01011", 28000, ["nifty_midcap100"]),
        ("ANGELONE", "Angel One Ltd", "Financial Services", "Capital Markets", "INE732I01013", 22000, ["nifty_midcap100"]),
        ("BSE", "BSE Ltd", "Financial Services", "Capital Markets", "INE118H01025", 32000, ["nifty_midcap100"]),
        ("MCX", "Multi Commodity Exchange of India Ltd", "Financial Services", "Capital Markets", "INE745G01035", 18000, ["nifty_midcap100"]),
        ("MAZDOCK", "Mazagon Dock Shipbuilders Ltd", "Industrials", "Shipbuilding", "INE249Z01012", 55000, ["nifty_midcap100"]),
        ("HINDCOPPER", "Hindustan Copper Ltd", "Materials", "Mining", "INE531E01026", 22000, ["nifty_midcap100"]),
        ("ASTRAL", "Astral Ltd", "Industrials", "Building Products", "INE006I01046", 40000, ["nifty_midcap100"]),
        ("SUPREMEIND", "Supreme Industries Ltd", "Industrials", "Building Products", "INE195A01028", 38000, ["nifty_midcap100"]),
        ("SUNDARMFIN", "Sundaram Finance Ltd", "Financial Services", "Consumer Finance", "INE660A01013", 36000, ["nifty_midcap100"]),
        ("SYNGENE", "Syngene International Ltd", "Healthcare", "Contract Research", "INE398R01022", 24000, ["nifty_midcap100"]),
        ("TATACHEM", "Tata Chemicals Ltd", "Materials", "Commodity Chemicals", "INE092A01019", 25000, ["nifty_midcap100"]),
        ("ABCAPITAL", "Aditya Birla Capital Ltd", "Financial Services", "Holding Companies", "INE674K01013", 38000, ["nifty_midcap100"]),
        ("IIFL", "IIFL Finance Ltd", "Financial Services", "Consumer Finance", "INE530B01024", 14000, ["nifty_midcap100"]),
        ("SUMICHEM", "Sumitomo Chemical India Ltd", "Materials", "Agrochemicals", "INE258G01013", 18000, ["nifty_midcap100"]),
        ("INDUSTOWER", "Indus Towers Ltd", "Communication Services", "Telecom Infrastructure", "INE121J01017", 80000, ["nifty_next50"]),
        ("DIXON", "Dixon Technologies (India) Ltd", "Consumer Durables", "Electronics Manufacturing", "INE935N01020", 52000, ["nifty_next50"]),
        ("OFSS", "Oracle Financial Services Software Ltd", "Information Technology", "IT Services & Consulting", "INE881D01027", 55000, ["nifty_midcap100"]),
        ("ESCORTS", "Escorts Kubota Ltd", "Automobile", "Farm Equipment", "INE042A01014", 30000, ["nifty_midcap100"]),
        ("RVNL", "Rail Vikas Nigam Ltd", "Industrials", "Construction & Engineering", "INE415G01027", 55000, ["nifty_midcap100"]),
    ]

    con.executemany(
        "INSERT OR IGNORE INTO dim_stocks VALUES (?, ?, ?, ?, ?, ?, ?)",
        [list(s) for s in extra_stocks],
    )
    logger.info(f"Seeded {len(extra_stocks)} Nifty 200 stocks (beyond Nifty 50)")
    return len(extra_stocks)


def load_historical_prices(con: duckdb.DuckDBPyConnection, period: str = "5y") -> int:
    """Load historical OHLCV data for all stocks in dim_stocks via yfinance."""
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
        stocks += _seed_nifty200_stocks(con)
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
