"""
Correction Loop — taxonomy-driven retry on SQL execution errors.
Adapted from MediaFlowAI. Max 2 retries.
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from src.agents.nlq.llm_provider import complete, get_llm
from src.agents.nlq.text2sql.schema_linker import get_schema_context
from src.agents.nlq.text2sql.sql_generator import _postprocess_sql

MAX_RETRIES = 2

_EXECUTION_ERROR_MAP = [
    ("Binder Error: Referenced column",  "schema_link",  "col_missing"),
    ("Binder Error: Table",              "schema_link",  "table_missing"),
    ("Catalog Error",                    "schema_link",  "table_missing"),
    ("Parser Error",                     "syntax",       "sql_syntax_error"),
    ("Invalid Input Error: Conversion",  "duckdb",       "wrong_cast_syntax"),
    ("Constraint Error",                 "filter",       "condition_type_mismatch"),
]


def classify_execution_error(error: str) -> tuple[str, str]:
    for substring, category, code in _EXECUTION_ERROR_MAP:
        if substring in error:
            return category, code
    return "syntax", "unknown"


class CorrectionPlan(BaseModel):
    error_category: str = "syntax"
    error_code: str = "unknown"
    root_cause: str = ""
    fix_steps: list[str] = Field(default_factory=list)
    key_rule: str = ""


_CORRECTION_SQL_PROMPT = """You are a DuckDB SQL correction agent for financial analytics.

Schema:
{schema}

Original question: {question}
Wrong SQL:
{wrong_sql}

Error: {error}
Correction plan:
{plan}

Write the corrected DuckDB SQL SELECT query. Apply ONLY the described fixes.
Return ONLY the corrected SQL, no explanation."""


def _get_correction_plan(
    question: str, wrong_sql: str, error: str,
    category: str, code: str, scratchpad: str,
) -> CorrectionPlan:
    prompt = (
        f"DuckDB SQL correction — {category} error.\n\n"
        f"Schema:\n{get_schema_context()}\n"
        f"Question: {question}\nWrong SQL:\n{wrong_sql}\n"
        f"Error: {error}\nPrior: {scratchpad or 'None'}\n\n"
        "Produce a CorrectionPlan with root_cause, fix_steps, key_rule."
    )
    try:
        llm = get_llm(temperature=0.0).with_structured_output(CorrectionPlan)
        result = llm.invoke(prompt)
        result.error_category = category
        result.error_code = code
        return result
    except Exception:
        try:
            raw = complete(prompt, max_tokens=512)
            return CorrectionPlan(error_category=category, error_code=code,
                                  root_cause=raw[:200], fix_steps=[raw], key_rule="Fix SQL")
        except Exception:
            return CorrectionPlan(error_category=category, error_code=code,
                                  root_cause=error[:100], fix_steps=["Rewrite query"],
                                  key_rule="Follow DuckDB syntax")


def _generate_corrected_sql(question: str, wrong_sql: str, correction: CorrectionPlan) -> str:
    plan_text = "\n".join(
        [f"Root cause: {correction.root_cause}"]
        + [f"{i+1}. {s}" for i, s in enumerate(correction.fix_steps)]
    )
    prompt = _CORRECTION_SQL_PROMPT.format(
        schema=get_schema_context(), question=question,
        wrong_sql=wrong_sql, error=correction.root_cause, plan=plan_text,
    )
    return _postprocess_sql(complete(prompt, max_tokens=1024))


def run_correction_loop(
    question: str, sql: str, execute_fn,
    initial_violations: list | None = None,
) -> tuple[str, list[dict] | None, str | None, list[str]]:
    """Execute SQL with up to MAX_RETRIES correction attempts."""
    correction_log: list[str] = []
    scratchpad_entries: list[str] = []
    current_sql = sql
    last_error: str | None = None

    for attempt in range(MAX_RETRIES + 1):
        result, error = execute_fn(current_sql)
        if error is None:
            return current_sql, result, None, correction_log

        last_error = error
        if attempt >= MAX_RETRIES:
            break

        if attempt == 0 and initial_violations:
            v = initial_violations[0]
            category, code = v.category, v.code
        else:
            category, code = classify_execution_error(error)

        correction_log.append(f"attempt_{attempt+1}: {category}/{code} — {error[:80]}")

        scratchpad = "\n".join(f"Attempt {i+1}: {e}" for i, e in enumerate(scratchpad_entries))
        correction = _get_correction_plan(question, current_sql, error, category, code, scratchpad)
        current_sql = _generate_corrected_sql(question, current_sql, correction)
        scratchpad_entries.append(error)
        correction_log.append(f"attempt_{attempt+1}_applied: {correction.key_rule or 'fix applied'}")

    return current_sql, None, last_error, correction_log
