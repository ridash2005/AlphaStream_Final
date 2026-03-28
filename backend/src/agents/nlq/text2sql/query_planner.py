"""
Query Planner — CoT step-by-step SQL plan before generation.
Adapted from MediaFlowAI for financial analytics.
"""
from __future__ import annotations
from typing import Union
from pydantic import BaseModel, Field
from src.agents.nlq.llm_provider import complete, get_llm
from src.agents.nlq.text2sql.schema_linker import get_schema_context, SchemaLink


class QueryPlan(BaseModel):
    steps: list[str] = Field(default_factory=list)
    tables_used: list[str] = Field(default_factory=lambda: ["dim_stocks"])
    aggregation_strategy: str = "none"
    requires_join: bool = False
    duckdb_notes: list[str] = Field(default_factory=list)


def plan_query(question: str, linked_columns: Union[dict[str, str], SchemaLink]) -> QueryPlan:
    """Returns QueryPlan for the SQL query."""
    if isinstance(linked_columns, SchemaLink):
        cols_dict = linked_columns.columns
    else:
        cols_dict = linked_columns

    cols_str = "\n".join(f"- {col}: {reason}" for col, reason in cols_dict.items()) or "all columns"

    try:
        llm = get_llm(temperature=0.7).with_structured_output(QueryPlan)
        prompt = (
            f"You are a SQL query planning agent for a DuckDB financial analytics database.\n\n"
            f"Schema:\n{get_schema_context()}\n\n"
            f"Relevant columns: {cols_str}\n\n"
            f"Question: {question}\n\n"
            "Produce a QueryPlan with:\n"
            "- steps: numbered CoT steps for the SQL query\n"
            "- tables_used: DuckDB tables/views referenced\n"
            "- aggregation_strategy: 'none', 'simple_count', 'grouped_agg', or 'window_function'\n"
            "- requires_join: true if multiple tables joined\n"
            "- duckdb_notes: DuckDB-specific syntax reminders\n\n"
            "DuckDB rules: current_date for dates, 'nifty50' = ANY(index_membership) for arrays."
        )
        return llm.invoke(prompt)
    except Exception:
        pass

    # Fallback
    try:
        prompt = (
            f"Schema:\n{get_schema_context()}\n\n"
            f"Columns: {cols_str}\n\nQuestion: {question}\n\n"
            "Write numbered steps for the SQL query:"
        )
        raw = complete(prompt, max_tokens=512)
        steps = [line.strip() for line in raw.splitlines() if line.strip()]
        return QueryPlan(steps=steps, aggregation_strategy="unknown")
    except Exception:
        return QueryPlan(steps=["SELECT * FROM v_stock_screener LIMIT 10"])
