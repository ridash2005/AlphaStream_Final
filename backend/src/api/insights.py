"""
Ambient Insights Engine — background generation of market alerts.

Runs every 30 minutes, checks thresholds, writes to DuckDB insights table.
"""
import logging
import uuid
from datetime import datetime

import duckdb

from src.data.market_schema import get_db_path

logger = logging.getLogger(__name__)


def generate_insights() -> int:
    """Generate insights from current market data. Returns count of new insights."""
    con = duckdb.connect(get_db_path())
    try:
        count = 0

        # 1. High Alpha Score signals
        rows = con.execute("""
            SELECT s.ticker, d.company_name, s.signal_type, s.direction,
                   s.alpha_score, s.confidence
            FROM fact_signals s
            JOIN dim_stocks d ON s.ticker = d.ticker
            WHERE s.alpha_score >= 80
              AND s.signal_date >= current_date - INTERVAL '3 days'
            ORDER BY s.alpha_score DESC LIMIT 5
        """).fetchall()
        for ticker, name, sig_type, direction, score, conf in rows:
            _upsert_insight(con, "alert", "warning",
                f"{name} ({ticker}) Alpha Score {score:.0f}",
                f"{direction.title()} {sig_type} signal with confidence {conf:.0f}%. Alpha Score {score:.1f} exceeded threshold of 80.",
                ticker, score, 80)
            count += 1

        # 2. Sector heatmap — sectors with most bullish signals
        rows = con.execute("""
            SELECT sector, bullish_count, signal_count, avg_alpha_score
            FROM v_sector_heatmap
            WHERE bullish_count >= 3
            ORDER BY bullish_count DESC LIMIT 3
        """).fetchall()
        for sector, bullish, total, avg_alpha in rows:
            _upsert_insight(con, "insight", "success",
                f"{sector}: {bullish} bullish signals",
                f"{sector} sector has {bullish} bullish signals out of {total} total (avg Alpha Score {avg_alpha:.1f}).",
                sector, float(bullish), 3)
            count += 1

        # 3. Recent insider activity
        rows = con.execute("""
            SELECT ticker, person_name, trade_type, quantity, value_lakhs
            FROM v_insider_activity_30d
            WHERE trade_date >= current_date - INTERVAL '7 days'
              AND value_lakhs > 50
            ORDER BY value_lakhs DESC LIMIT 3
        """).fetchall()
        for ticker, person, trade_type, qty, value in rows:
            severity = "warning" if trade_type == "sell" else "success"
            _upsert_insight(con, "alert", severity,
                f"Insider {trade_type}: {ticker} by {person}",
                f"{person} {trade_type} {qty:,} shares of {ticker} worth Rs {value:.1f}L.",
                ticker, float(value), 50)
            count += 1

        logger.info(f"Generated {count} insights")
        return count
    finally:
        con.close()


def _upsert_insight(con, type_: str, severity: str, title: str, body: str,
                    ticker: str, value: float, threshold: float):
    """Insert insight if a similar one doesn't already exist today."""
    existing = con.execute("""
        SELECT count(*) FROM insights
        WHERE title = ? AND created_at >= current_date
        AND dismissed = false
    """, [title]).fetchone()[0]

    if existing == 0:
        con.execute("""
            INSERT INTO insights (id, type, severity, title, body, ticker, value, threshold)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [str(uuid.uuid4())[:8], type_, severity, title, body, ticker, value, threshold])


def seed_initial_insights():
    """Seed insights on startup if table is empty."""
    con = duckdb.connect(get_db_path())
    try:
        count = con.execute("SELECT count(*) FROM insights").fetchone()[0]
        if count == 0:
            generate_insights()
            logger.info("Seeded initial insights")
    except Exception as e:
        logger.warning(f"Failed to seed insights: {e}")
    finally:
        con.close()
