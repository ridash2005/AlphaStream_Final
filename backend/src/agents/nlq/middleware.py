"""
AlphaStream India NLQ agent middleware — input, output, and tool-call guardrails.

Adapted from MediaFlowAI middleware for financial market domain.
"""
from __future__ import annotations
import re
from src.agents.nlq.graph_state import AgentState

# ── PII patterns ───────────────────────────────────────────────────────────────
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
_PHONE_RE = re.compile(r"\b(\+?91[-.\s]?)?\d{10}\b|\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")

# ── Injection patterns ─────────────────────────────────────────────────────────
_INJECTION_RE = re.compile(
    r"\b(ignore previous instructions?|disregard|you are now|pretend you are|"
    r"act as|jailbreak|DAN|do anything now)\b",
    re.IGNORECASE,
)

# ── Sensitive content patterns (hard block) ────────────────────────────────────
_SENSITIVE_RE = re.compile(
    r"\b(password|credit\s*card|ssn|social\s*security|bank\s*account|"
    r"delete\s+database|drop\s+table)\b",
    re.IGNORECASE,
)

# ── Tech name leakage patterns (output guardrail) ─────────────────────────────
_TECH_NAME_RE = re.compile(
    r"\b(DuckDB|LangChain|LangGraph|OpenRouter|FastMCP|ChromaDB|"
    r"FastAPI|uvicorn|Python|pandas|numpy|Pathway|yfinance)\b",
    re.IGNORECASE,
)

_TECH_REPLACEMENTS = {
    "duckdb": "our analytics engine",
    "langchain": "our AI system",
    "langgraph": "our AI system",
    "openrouter": "our AI system",
    "fastmcp": "our analytics engine",
    "chromadb": "our analytics engine",
    "fastapi": "our platform",
    "uvicorn": "our platform",
    "python": "our analytics engine",
    "pandas": "our analytics engine",
    "numpy": "our analytics engine",
    "pathway": "our streaming engine",
    "yfinance": "our market data provider",
}


def _redact_tech_names(text: str) -> str:
    """Replace technology names with generic terms."""
    def _replace(match):
        key = match.group(0).lower().strip()
        return _TECH_REPLACEMENTS.get(key, "our analytics engine")
    return _TECH_NAME_RE.sub(_replace, text)


_OFF_TOPIC_NARRATIVE = (
    "I can only answer questions about the Indian stock market: "
    "stock signals, insider trades, FII/DII flows, chart patterns, portfolio analysis, "
    "and corporate filings.\n\n"
    "Try asking:\n"
    '- "What signals fired today?"\n'
    '- "Show me insider buying in IT sector"\n'
    '- "What are FIIs doing this week?"\n'
    '- "Which stocks have RSI below 30?"'
)


class AlphaStreamInputGuardrail:
    """Before-agent hook: validates and sanitizes inbound user query."""

    def before_agent(self, state: AgentState) -> AgentState:
        return self._check(state)

    def _check(self, state: AgentState) -> AgentState:
        query = state.get("query", "")
        violations: list[str] = []
        sanitized = query

        # 1. PII redaction
        if _EMAIL_RE.search(query):
            sanitized = _EMAIL_RE.sub("[EMAIL]", sanitized)
            violations.append("pii:email_redacted")
        if _PHONE_RE.search(sanitized):
            sanitized = _PHONE_RE.sub("[PHONE]", sanitized)
            violations.append("pii:phone_redacted")

        # 2. Injection detection (flag only)
        if _INJECTION_RE.search(query):
            violations.append("injection:prompt_injection_detected")

        # 3. Sensitive content hard block
        if _SENSITIVE_RE.search(query):
            return {
                **state,
                "error": "Query blocked: sensitive content detected.",
                "narrative": "I can only answer questions about Indian stock market analytics.",
                "input_guardrail_violations": violations + ["scope:blocked"],
                "pii_redacted": bool(violations),
            }

        return {
            **state,
            "query": sanitized,
            "input_guardrail_violations": violations,
            "pii_redacted": bool(violations),
        }


class AlphaStreamOutputGuardrail:
    """After-agent hook: validates agent narrative output."""

    def after_agent(self, state: AgentState) -> AgentState:
        return self._check(state)

    def _check(self, state: AgentState) -> AgentState:
        narrative = state.get("narrative") or ""
        violations: list[str] = []

        # Redact PII leakage
        if _EMAIL_RE.search(narrative):
            narrative = _EMAIL_RE.sub("[EMAIL]", narrative)
            violations.append("output_pii:email_leaked")
        if _PHONE_RE.search(narrative):
            narrative = _PHONE_RE.sub("[PHONE]", narrative)
            violations.append("output_pii:phone_leaked")

        # Tech name leakage
        if _TECH_NAME_RE.search(narrative):
            narrative = _redact_tech_names(narrative)
            violations.append("output:tech_name_leaked")

        # Empty narrative
        if not narrative.strip():
            narrative = "I was unable to generate a response. Please rephrase your question."
            violations.append("output:empty_narrative")

        return {
            **state,
            "narrative": narrative,
            "output_guardrail_violations": violations,
        }
