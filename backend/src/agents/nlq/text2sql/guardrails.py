"""
Guardrails — LLM-based SQL validator for financial analytics DuckDB.
Adapted from MediaFlowAI. DDL/DML blocking is regex (security hard-stop).
"""
from __future__ import annotations
import logging
import re
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableLambda

logger = logging.getLogger(__name__)


class GuardrailViolation(BaseModel):
    category: str
    code: str
    message: str
    sql_fragment: Optional[str] = None


class GuardrailResult(BaseModel):
    safe: bool
    violations: list[GuardrailViolation] = Field(default_factory=list)
    primary_category: Optional[str] = None


ERROR_TAXONOMY = {
    "syntax":      ["sql_syntax_error", "ddl_dml_blocked", "not_select", "sql_too_long"],
    "schema_link": ["table_missing", "col_missing", "ambiguous_col"],
    "filter":      ["where_missing", "condition_wrong_col", "value_format_wrong"],
    "aggregation": ["agg_no_groupby", "groupby_missing_col", "having_without_groupby"],
    "duckdb":      ["wrong_cast_syntax", "wrong_boolean_compare"],
}

_MAX_SQL_LEN = 50_000
_SEVERITY_ORDER = ["syntax", "duckdb", "schema_link", "aggregation", "filter"]

_DDL_DML_PATTERN = re.compile(
    r"\b(UPDATE|DELETE|DROP|INSERT|CREATE|ALTER|TRUNCATE|REPLACE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)
_PG_CAST_PATTERN = re.compile(r"::[A-Za-z]")

_VALIDATION_PROMPT = """You are a DuckDB SQL validator for an Indian stock market analytics platform.

Evaluate the SQL below against the schema and DuckDB rules.

=== SQL TO VALIDATE ===
{sql}

=== SCHEMA ===
Tables: dim_stocks, fact_daily_prices, fact_signals, fact_insider_trades,
        fact_fii_dii_flows, fact_filings, fact_quarterly_results
Views: v_signal_summary, v_insider_activity_30d, v_fii_dii_trend,
       v_sector_heatmap, v_stock_screener

dim_stocks columns: ticker, company_name, sector, industry, isin, market_cap_cr, index_membership
fact_daily_prices columns: ticker, date, open, high, low, close, volume, adj_close
fact_signals columns: signal_id, ticker, signal_date, signal_type, direction, confidence, alpha_score, evidence_json, backtest_json
fact_insider_trades columns: id, ticker, person_name, person_category, trade_type, quantity, value_lakhs, trade_date
fact_fii_dii_flows columns: date, fii_buy_cr, fii_sell_cr, fii_net_cr, dii_buy_cr, dii_sell_cr, dii_net_cr

=== VALID DIMENSION VALUES ===
sector: Financial Services, Information Technology, Energy, Automobile, Healthcare, Fast Moving Consumer Goods, Materials, Industrials, Consumer Durables, Utilities
signal_type: technical, filing, insider, flow, sentiment
direction: bullish, bearish, neutral
trade_type: buy, sell
person_category: promoter, director, kmp
materiality: high, medium, low

=== RULES ===
[duckdb / wrong_cast_syntax] Never use ::TYPE. Use CAST() or TRY_CAST().
[aggregation / agg_no_groupby] Non-aggregated columns in SELECT with aggregates need GROUP BY.
[filter / value_format_wrong] String values must match dimension values exactly (case-sensitive).
[schema_link / col_missing] All column names must exist in the referenced table.

=== RESPONSE ===
Return safe=true with empty violations if no issues. For violations, use exact category/code from brackets above."""


def _llm_validate(sql: str) -> GuardrailResult:
    try:
        from src.agents.nlq.llm_provider import get_llm
        llm = get_llm(temperature=0.0).with_structured_output(GuardrailResult)
        result = llm.invoke(_VALIDATION_PROMPT.format(sql=sql))
        if result.violations and not result.primary_category:
            result.primary_category = classify_violation(result.violations)
        return result
    except Exception as e:
        logger.warning("LLM SQL validation failed, skipping LLM check: %s", e)
        return GuardrailResult(safe=True)


def check_all(sql: str) -> GuardrailResult:
    """Validate SQL. DDL/DML regex hard-stop, then LLM validation."""
    m = _DDL_DML_PATTERN.search(sql)
    if m:
        v = GuardrailViolation(category="syntax", code="ddl_dml_blocked",
                               message=f"Blocked: {m.group(0)}", sql_fragment=m.group(0))
        return GuardrailResult(safe=False, violations=[v], primary_category="syntax")

    m_cast = _PG_CAST_PATTERN.search(sql)
    if m_cast:
        v = GuardrailViolation(category="duckdb", code="wrong_cast_syntax",
                               message="Use CAST() not ::", sql_fragment=m_cast.group(0))
        return GuardrailResult(safe=False, violations=[v], primary_category="duckdb")

    if len(sql) > _MAX_SQL_LEN:
        v = GuardrailViolation(category="syntax", code="sql_too_long",
                               message=f"SQL exceeds {_MAX_SQL_LEN} chars")
        return GuardrailResult(safe=False, violations=[v], primary_category="syntax")

    return _llm_validate(sql)


def classify_violation(violations: list[GuardrailViolation]) -> str:
    found = {v.category for v in violations}
    for cat in _SEVERITY_ORDER:
        if cat in found:
            return cat
    return violations[0].category if violations else "unknown"


guardrail_runnable: RunnableLambda = RunnableLambda(check_all)


def check(sql: str) -> tuple[bool, list[str]]:
    result = check_all(sql)
    errors = [v.message for v in result.violations if v.category in ("syntax", "duckdb")]
    return (not bool(errors), errors)
