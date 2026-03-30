"""
Signal Writer — persists agent detections to DuckDB.

Bridges the gap between agents (which return dicts) and DuckDB (which stores signals).
"""
import logging
import uuid
from datetime import datetime

import duckdb

from src.data.market_schema import get_db_path

logger = logging.getLogger(__name__)


def write_signal(
    ticker: str,
    signal_type: str,
    direction: str,
    confidence: float,
    alpha_score: float = 0,
    evidence: dict = None,
    backtest: dict = None,
) -> bool:
    """Write a detected signal to fact_signals. Deduplicates by ticker+type+date."""
    con = duckdb.connect(get_db_path())
    try:
        existing = con.execute("""
            SELECT count(*) FROM fact_signals
            WHERE ticker = ? AND signal_type = ? AND signal_date = current_date
              AND json_extract_string(evidence_json, '$.pattern') = ?
        """, [ticker, signal_type, (evidence or {}).get("pattern", "")]).fetchone()[0]

        if existing > 0:
            return False

        import json
        con.execute("""
            INSERT INTO fact_signals (signal_id, ticker, signal_date, signal_type, direction,
                                     confidence, alpha_score, evidence_json, backtest_json)
            VALUES (?, ?, current_date, ?, ?, ?, ?, ?, ?)
        """, [
            str(uuid.uuid4())[:8], ticker, signal_type, direction,
            confidence, alpha_score,
            json.dumps(evidence or {}), json.dumps(backtest or {}),
        ])
        return True
    except Exception as e:
        logger.warning(f"Signal write failed: {e}")
        return False
    finally:
        con.close()


def write_fii_dii(date_str: str, fii_buy: float, fii_sell: float,
                  dii_buy: float, dii_sell: float) -> bool:
    """Write FII/DII flow data. Deduplicates by date."""
    con = duckdb.connect(get_db_path())
    try:
        existing = con.execute("SELECT count(*) FROM fact_fii_dii_flows WHERE date = ?",
                               [date_str]).fetchone()[0]
        if existing > 0:
            return False
        con.execute("""
            INSERT INTO fact_fii_dii_flows VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [date_str, fii_buy, fii_sell, round(fii_buy - fii_sell, 2),
              dii_buy, dii_sell, round(dii_buy - dii_sell, 2)])
        return True
    except Exception as e:
        logger.warning(f"FII/DII write failed: {e}")
        return False
    finally:
        con.close()


def write_insider_trade(trade: dict) -> bool:
    """Write insider trade. Deduplicates by ticker+person+date."""
    con = duckdb.connect(get_db_path())
    try:
        existing = con.execute("""
            SELECT count(*) FROM fact_insider_trades
            WHERE ticker = ? AND person_name = ? AND trade_date = ?
        """, [trade.get("ticker", ""), trade.get("person_name", ""),
              trade.get("trade_date", "")]).fetchone()[0]
        if existing > 0:
            return False
        con.execute("""
            INSERT INTO fact_insider_trades (id, ticker, person_name, person_category,
                                            trade_type, quantity, value_lakhs, trade_date, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            str(uuid.uuid4())[:8], trade.get("ticker", ""), trade.get("person_name", ""),
            trade.get("person_category", ""), trade.get("trade_type", ""),
            trade.get("quantity", 0), trade.get("value_lakhs", 0),
            trade.get("trade_date", ""), trade.get("source", "NSE"),
        ])
        return True
    except Exception as e:
        logger.warning(f"Insider write failed: {e}")
        return False
    finally:
        con.close()
