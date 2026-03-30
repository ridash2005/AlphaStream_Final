"""
SQL Generator — produces DuckDB SQL from the CoT plan.
Adapted from MediaFlowAI for financial analytics.
"""
from __future__ import annotations
import re
from typing import Union
from pydantic import BaseModel, Field
from src.agents.nlq.llm_provider import complete, get_llm
from src.agents.nlq.text2sql.schema_linker import get_schema_context


class GeneratedSQL(BaseModel):
    sql: str = ""
    confidence: float = 0.5
    warnings: list[str] = Field(default_factory=list)


def generate_sql(question: str, plan: Union["QueryPlan", str]) -> GeneratedSQL:  # noqa: F821
    """Returns GeneratedSQL from the query plan."""
    if hasattr(plan, "steps"):
        plan_str = "\n".join(f"{i+1}. {s}" for i, s in enumerate(plan.steps))
    else:
        plan_str = str(plan)

    try:
        llm = get_llm(temperature=0.0).with_structured_output(GeneratedSQL)
        prompt = (
            "You are a DuckDB SQL generation agent for Indian stock market analytics.\n\n"
            "CRITICAL: Generate ONLY SELECT statements. NEVER generate DELETE, DROP, ALTER, "
            "TRUNCATE, UPDATE, INSERT, CREATE, GRANT, REVOKE.\n\n"
            f"Schema:\n{get_schema_context()}\n\n"
            f"Question: {question}\n\n"
            f"Query plan:\n{plan_str}\n\n"
            "Produce a GeneratedSQL with:\n"
            "- sql: complete DuckDB SELECT query (no markdown fences)\n"
            "- confidence: float 0.0-1.0\n"
            "- warnings: any known limitations\n\n"
            "DuckDB rules:\n"
            "- current_date for today, INTERVAL for date math\n"
            "- 'nifty50' = ANY(index_membership) for array contains\n"
            "- json_extract_string(evidence_json, '$.pattern') for JSON access\n"
            "- ONLY SELECT — no DDL/DML"
        )
        result = llm.invoke(prompt)
        result.sql = _postprocess_sql(result.sql)
        return result
    except Exception:
        pass

    # Fallback
    try:
        prompt = (
            "Generate a DuckDB SELECT query. ONLY SELECT, no DDL/DML.\n\n"
            f"Schema:\n{get_schema_context()}\n\n"
            f"Question: {question}\nPlan:\n{plan_str}\n\n"
            "Return ONLY the SQL, no explanation."
        )
        raw = complete(prompt, max_tokens=1024)
        return GeneratedSQL(sql=_postprocess_sql(raw), confidence=0.5)
    except Exception:
        return GeneratedSQL(
            sql="SELECT * FROM v_stock_screener LIMIT 10",
            confidence=0.1,
            warnings=["Fallback SQL — generation failed"],
        )


def _postprocess_sql(raw: str) -> str:
    """Strip markdown fences and rewrite unsupported DuckDB syntax."""
    raw = re.sub(r"```(?:sql)?\s*", "", raw)
    raw = re.sub(r"```", "", raw)
    # Rewrite PostgreSQL-style JSON operator to DuckDB json_extract_string()
    raw = re.sub(
        r"(\w+)->>\'([^\']+)\'",
        r"json_extract_string(\1, '$.\2')",
        raw,
    )
    raw = re.sub(
        r"(\w+)->>\"([^\"]+)\"",
        r"json_extract_string(\1, '$.\2')",
        raw,
    )
    return raw.strip()
