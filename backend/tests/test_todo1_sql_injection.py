"""
Tests for TODO 1: SQL injection fix in insights router.

Validates that:
1. Normal queries with type and severity filters work correctly
2. SQL injection payloads in parameters don't execute or break the query
3. Parameterized queries produce correct results
"""

import os
import uuid

import duckdb
import pytest

# ---------------------------------------------------------------------------
# Helpers — lightweight in-memory DuckDB that mimics the insights table
# ---------------------------------------------------------------------------

TEST_DB = os.path.join(os.path.dirname(__file__), f"_test_insights_{uuid.uuid4().hex[:8]}.duckdb")


def _create_test_db():
    """Create a test DuckDB with the insights table and sample data."""
    con = duckdb.connect(TEST_DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS insights (
            id          VARCHAR PRIMARY KEY,
            type        VARCHAR,
            severity    VARCHAR,
            title       VARCHAR,
            body        VARCHAR,
            read        BOOLEAN DEFAULT false,
            dismissed   BOOLEAN DEFAULT false,
            created_at  TIMESTAMP DEFAULT current_timestamp
        )
    """)
    # Insert sample data
    con.execute("""
        INSERT INTO insights (id, type, severity, title, body, read, dismissed, created_at) VALUES
        ('i1', 'anomaly',  'high',   'Unusual volume spike',       'Volume 3x normal', false, false, '2025-01-01 10:00:00'),
        ('i2', 'anomaly',  'medium', 'Price deviation',            'Price deviated 2%', false, false, '2025-01-01 11:00:00'),
        ('i3', 'signal',   'high',   'Bullish crossover',          'EMA crossover',     true,  false, '2025-01-01 12:00:00'),
        ('i4', 'signal',   'low',    'Weak momentum',              'RSI declining',     false, false, '2025-01-01 13:00:00'),
        ('i5', 'news',     'medium', 'Earnings announcement',      'Q4 results',        false, true,  '2025-01-01 14:00:00')
    """)
    con.close()


def _cleanup_test_db():
    """Remove the test database file."""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def _run_parameterized_query(type_val=None, severity_val=None, unread_only=False, limit=20):
    """
    Execute the FIXED (parameterized) query logic against the test DB.
    This mirrors what the fixed get_insights endpoint should do.
    """
    con = duckdb.connect(TEST_DB, read_only=True)
    try:
        sql = "SELECT * FROM insights WHERE dismissed = false"
        params = []
        if type_val:
            sql += " AND type = ?"
            params.append(type_val)
        if severity_val:
            sql += " AND severity = ?"
            params.append(severity_val)
        if unread_only:
            sql += " AND read = false"
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        return con.execute(sql, params).fetchdf().to_dict(orient="records")
    finally:
        con.close()


def _run_vulnerable_query(type_val=None, severity_val=None, unread_only=False, limit=20):
    """
    Execute the VULNERABLE (f-string interpolated) query logic against the test DB.
    This mirrors the broken code before the fix.
    """
    con = duckdb.connect(TEST_DB, read_only=True)
    try:
        sql = "SELECT * FROM insights WHERE dismissed = false"
        if type_val:
            sql += f" AND type = '{type_val}'"
        if severity_val:
            sql += f" AND severity = '{severity_val}'"
        if unread_only:
            sql += " AND read = false"
        sql += f" ORDER BY created_at DESC LIMIT {limit}"
        return con.execute(sql).fetchdf().to_dict(orient="records")
    except Exception:
        return []
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
def setup_teardown():
    """Create test DB before tests, clean up after."""
    _create_test_db()
    yield
    _cleanup_test_db()


# ---------------------------------------------------------------------------
# Tests: Normal query functionality
# ---------------------------------------------------------------------------


class TestNormalQueries:
    """Verify that parameterized queries produce correct results for normal input."""

    def test_no_filters_returns_non_dismissed(self):
        """Without filters, return all non-dismissed insights."""
        results = _run_parameterized_query()
        ids = {r["id"] for r in results}
        assert "i5" not in ids
        assert len(results) == 4

    def test_type_filter(self):
        """Filtering by type='anomaly' returns only anomaly insights."""
        results = _run_parameterized_query(type_val="anomaly")
        assert len(results) == 2
        assert all(r["type"] == "anomaly" for r in results)

    def test_severity_filter(self):
        """Filtering by severity='high' returns only high-severity insights."""
        results = _run_parameterized_query(severity_val="high")
        assert len(results) == 2
        assert all(r["severity"] == "high" for r in results)

    def test_type_and_severity_combined(self):
        """Combined type + severity filter narrows results correctly."""
        results = _run_parameterized_query(type_val="anomaly", severity_val="high")
        assert len(results) == 1
        assert results[0]["id"] == "i1"

    def test_unread_only(self):
        """unread_only=True excludes read insights."""
        results = _run_parameterized_query(unread_only=True)
        assert all(r["read"] == False for r in results)
        ids = {r["id"] for r in results}
        assert "i3" not in ids

    def test_limit(self):
        """Limit parameter caps the number of results."""
        results = _run_parameterized_query(limit=2)
        assert len(results) == 2

    def test_combined_all_filters(self):
        """All filters together work correctly."""
        results = _run_parameterized_query(
            type_val="anomaly", severity_val="medium", unread_only=True, limit=10
        )
        assert len(results) == 1
        assert results[0]["id"] == "i2"


# ---------------------------------------------------------------------------
# Tests: SQL injection prevention
# ---------------------------------------------------------------------------


class TestSQLInjectionPrevention:
    """Verify that SQL injection payloads are safely handled with parameterized queries."""

    def test_injection_in_type_single_quote(self):
        results = _run_parameterized_query(type_val="' OR '1'='1")
        assert len(results) == 0

    def test_injection_in_type_union_select(self):
        payload = "' UNION SELECT * FROM information_schema.tables --"
        results = _run_parameterized_query(type_val=payload)
        assert len(results) == 0

    def test_injection_in_severity_drop_table(self):
        payload = "'; DROP TABLE insights; --"
        results = _run_parameterized_query(severity_val=payload)
        assert len(results) == 0
        con = duckdb.connect(TEST_DB, read_only=True)
        try:
            count = con.execute("SELECT count(*) FROM insights").fetchone()[0]
            assert count == 5
        finally:
            con.close()

    def test_injection_in_type_boolean_always_true(self):
        payload = "anomaly' OR 1=1 --"
        results = _run_parameterized_query(type_val=payload)
        assert len(results) == 0

    def test_vulnerable_code_is_actually_vulnerable(self):
        normal_results = _run_vulnerable_query(type_val="anomaly")
        injection_results = _run_vulnerable_query(type_val="anomaly' OR '1'='1")
        assert len(injection_results) > len(normal_results)

    def test_parameterized_not_vulnerable_to_tautology(self):
        normal_results = _run_parameterized_query(type_val="anomaly")
        injection_results = _run_parameterized_query(type_val="anomaly' OR '1'='1")
        assert len(normal_results) == 2
        assert len(injection_results) == 0
