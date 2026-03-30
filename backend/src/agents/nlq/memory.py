"""
Persistent Memory for NLQ Agent — DuckDB-backed.

Survives restarts. Stores user preferences, query patterns, and learned context.
"""
import json
import logging
from datetime import datetime
from typing import Any, Optional

import duckdb

from src.data.market_schema import get_db_path

logger = logging.getLogger(__name__)

_TABLE_CREATED = False


def _ensure_table():
    """Create memory table if it doesn't exist."""
    global _TABLE_CREATED
    if _TABLE_CREATED:
        return
    con = duckdb.connect(get_db_path())
    try:
        con.execute("""
            CREATE TABLE IF NOT EXISTS agent_memory (
                session_id VARCHAR,
                key        VARCHAR,
                value_json TEXT,
                created_at TIMESTAMP DEFAULT current_timestamp,
                updated_at TIMESTAMP DEFAULT current_timestamp,
                PRIMARY KEY (session_id, key)
            )
        """)
        _TABLE_CREATED = True
    finally:
        con.close()


def save_memory(session_id: str, key: str, value: Any) -> None:
    """Save a memory item (upsert)."""
    _ensure_table()
    con = duckdb.connect(get_db_path())
    try:
        val_json = json.dumps(value, default=str)
        existing = con.execute(
            "SELECT count(*) FROM agent_memory WHERE session_id = ? AND key = ?",
            [session_id, key],
        ).fetchone()[0]
        if existing > 0:
            con.execute(
                "UPDATE agent_memory SET value_json = ?, updated_at = current_timestamp WHERE session_id = ? AND key = ?",
                [val_json, session_id, key],
            )
        else:
            con.execute(
                "INSERT INTO agent_memory (session_id, key, value_json) VALUES (?, ?, ?)",
                [session_id, key, val_json],
            )
    finally:
        con.close()


def load_memory(session_id: str, key: str) -> Optional[Any]:
    """Load a memory item."""
    _ensure_table()
    con = duckdb.connect(get_db_path(), read_only=True)
    try:
        row = con.execute(
            "SELECT value_json FROM agent_memory WHERE session_id = ? AND key = ?",
            [session_id, key],
        ).fetchone()
        if row:
            try:
                return json.loads(row[0])
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("Corrupted memory for %s/%s: %s", session_id, key, e)
                return None
        return None
    finally:
        con.close()


def load_session_memories(session_id: str, limit: int = 20) -> list[dict]:
    """Load all memories for a session."""
    _ensure_table()
    con = duckdb.connect(get_db_path(), read_only=True)
    try:
        rows = con.execute(
            "SELECT key, value_json, updated_at FROM agent_memory WHERE session_id = ? ORDER BY updated_at DESC LIMIT ?",
            [session_id, limit],
        ).fetchall()
        result = []
        for k, v, t in rows:
            try:
                result.append({"key": k, "value": json.loads(v), "updated_at": str(t)})
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("Corrupted memory entry '%s' for session %s: %s", k, session_id, e)
        return result
    finally:
        con.close()


def save_query_pattern(session_id: str, query: str, intent: str) -> None:
    """Save a query pattern for learning user preferences."""
    _ensure_table()
    patterns = load_memory(session_id, "query_patterns") or []
    patterns.append({"query": query[:200], "intent": intent, "ts": datetime.now().isoformat()})
    # Keep last 50
    save_memory(session_id, "query_patterns", patterns[-50:])


def get_user_context(session_id: str) -> str:
    """Build context string from persistent memory for NLQ prompts."""
    patterns = load_memory(session_id, "query_patterns") or []
    portfolio = load_memory(session_id, "portfolio") or []

    parts = []
    if patterns:
        recent = patterns[-5:]
        intent_counts = {}
        for p in patterns:
            i = p.get("intent", "unknown")
            intent_counts[i] = intent_counts.get(i, 0) + 1
        top_intent = max(intent_counts, key=intent_counts.get) if intent_counts else "unknown"
        parts.append(f"User tends to ask about: {top_intent} (based on {len(patterns)} past queries)")

    if portfolio:
        tickers = [h.get("ticker", "") for h in portfolio]
        parts.append(f"User portfolio: {', '.join(tickers)}")

    return "\n".join(parts) if parts else ""
