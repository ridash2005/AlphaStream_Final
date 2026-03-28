"""LangGraph state schema for the AlphaStream India NLQ agent."""
from __future__ import annotations
from typing import Annotated, Any, Optional
from typing_extensions import TypedDict


def _last(a, b):
    """Reducer: last writer wins."""
    return b if b is not None else a


class AgentState(TypedDict, total=False):
    session_id: Annotated[str, _last]
    query: Annotated[str, _last]
    intent: Annotated[str, _last]
    filters: Annotated[dict[str, Any], _last]
    sql: Annotated[Optional[str], _last]
    result: Annotated[Optional[list[dict]], _last]
    chart_spec: Annotated[Optional[dict], _last]
    narrative: Annotated[Optional[str], _last]
    thought_steps: Annotated[list[dict], _last]
    history: Annotated[list[dict], _last]
    error: Annotated[Optional[str], _last]

    # Financial context
    portfolio_context: Annotated[Optional[str], _last]
    suggested_questions: Annotated[Optional[list[str]], _last]
    sources: Annotated[Optional[list[str]], _last]
    confidence: Annotated[Optional[str], _last]

    # Signal/KPI matching (set by router)
    _matched_signal: Annotated[Optional[str], _last]
    _signal_definition: Annotated[Optional[str], _last]

    # HITL fields
    hitl_pending: Annotated[bool, _last]
    hitl_payload: Annotated[Optional[dict], _last]
    hitl_decision: Annotated[Optional[str], _last]
    pending_inbox_items: Annotated[list[dict], _last]

    # Guardrail tracking
    input_guardrail_violations: Annotated[list[str], _last]
    output_guardrail_violations: Annotated[list[str], _last]
    pii_redacted: Annotated[bool, _last]
