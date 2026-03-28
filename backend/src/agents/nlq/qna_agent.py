"""
LangGraph NLQ Agent for AlphaStream India.

Adapted from MediaFlowAI qna_agent.py for Indian stock market analytics.
Graph: input_guardrail → router → {analytics | text2sql | narrate} → narrate → output_guardrail → END
"""
from __future__ import annotations

import concurrent.futures
import json
import time
from typing import Any, AsyncGenerator, Literal, Optional

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.store.base import BaseStore
from langgraph.types import Command

from src.agents.nlq.graph_state import AgentState
from src.agents.nlq.middleware import (
    AlphaStreamInputGuardrail,
    AlphaStreamOutputGuardrail,
    _OFF_TOPIC_NARRATIVE,
)
from src.data.market_schema import get_db_path

_SIMILARITY_THRESHOLD = 0.75
_SQL_TIMEOUT_SECS = 30
_MAX_RESULT_ROWS = 5_000

_store = InMemoryStore()


# ── DB executor ──────────────────────────────────────────────────────────────

def _execute_sql(sql: str) -> tuple[list[dict] | None, str | None]:
    """Execute SQL against DuckDB with timeout and row cap."""
    def _run():
        import duckdb
        conn = duckdb.connect(get_db_path(), read_only=True)
        try:
            rel = conn.execute(sql)
            rows = rel.fetchmany(_MAX_RESULT_ROWS + 1)
            cols = [d[0] for d in rel.description]
            return rows, cols
        finally:
            conn.close()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_run)
            rows, cols = future.result(timeout=_SQL_TIMEOUT_SECS)

        truncated = len(rows) > _MAX_RESULT_ROWS
        if truncated:
            rows = rows[:_MAX_RESULT_ROWS]

        result = [dict(zip(cols, r)) for r in rows]
        if truncated:
            result.append({"__truncated__": True, "__limit__": _MAX_RESULT_ROWS})
        return result, None

    except concurrent.futures.TimeoutError:
        return None, f"SQL timeout: query exceeded {_SQL_TIMEOUT_SECS}s limit"
    except Exception as e:
        return None, str(e)


# ── Guardrail singletons ─────────────────────────────────────────────────────

_input_guardrail = AlphaStreamInputGuardrail()
_output_guardrail = AlphaStreamOutputGuardrail()


# ── Guardrail nodes ──────────────────────────────────────────────────────────

def input_guardrail_node(state: AgentState) -> AgentState:
    return _input_guardrail.before_agent(state)


def output_guardrail_node(state: AgentState) -> AgentState:
    return _output_guardrail.after_agent(state)


# ── Router ───────────────────────────────────────────────────────────────────

_CLASSIFY_SYSTEM = (
    "You are the query router for AlphaStream India, an AI-powered Indian stock market analytics platform.\n"
    "The platform tracks: NSE/BSE stock signals, insider trades (SAST/PIT), FII/DII flows, "
    "chart patterns, corporate filings, portfolio analysis, and backtested signal performance.\n\n"
    "Available signal types: ALPHA_SCORE, RSI_DIVERGENCE, MACD_CROSSOVER, BOLLINGER_BREAKOUT, "
    "VOLUME_BREAKOUT, GOLDEN_CROSS, INSIDER_BUY, FII_STREAK, MATERIAL_FILING.\n\n"
    "Classify the user query into EXACTLY one category:\n\n"
    "GREETING — User is greeting or asking what you can do.\n\n"
    "OFF_TOPIC — Query has nothing to do with stocks, market, investing, trading, signals, "
    "filings, or financial data.\n\n"
    "SIGNAL_DEF:<NAME> — User asks what a specific signal means "
    "(e.g., 'What is RSI divergence?', 'Explain golden cross').\n\n"
    "SIGNAL_QUERY — User asks about detected signals, opportunities, alpha scores "
    "(e.g., 'What signals fired today?', 'Show bullish signals', 'Top opportunities').\n\n"
    "INSIDER_QUERY — User asks about insider trades, promoter buying/selling, SAST data "
    "(e.g., 'Any insider buying in IT?', 'Who bought INFY shares?').\n\n"
    "FLOW_QUERY — User asks about FII/DII flows, institutional activity "
    "(e.g., 'What are FIIs doing?', 'DII buying trend').\n\n"
    "STOCK_LOOKUP — User asks about a specific stock's data, price, fundamentals "
    "(e.g., 'Tell me about RELIANCE', 'TCS price').\n\n"
    "NEWS_QUERY — User asks about recent news, articles, market headlines "
    "(e.g., 'What news about RELIANCE?', 'Latest market headlines').\n\n"
    "PORTFOLIO_AWARE — User references 'my portfolio', 'my stocks', 'my holdings' "
    "(e.g., 'How does this affect my portfolio?').\n\n"
    "AD_HOC — Any other analytics question needing custom SQL "
    "(e.g., 'Compare IT vs Banking signals', 'Stocks with volume breakout this week').\n\n"
    "Respond with ONLY the classification label."
)


def _classify_query(query: str) -> str:
    """Single LLM call to classify query intent."""
    try:
        from src.agents.nlq.llm_provider import complete
        result = complete(
            prompt=f"User query: {query}",
            system=_CLASSIFY_SYSTEM,
            temperature=0.0,
            max_tokens=30,
        ).strip().upper()

        valid = ("OFF_TOPIC", "GREETING", "SIGNAL_QUERY", "INSIDER_QUERY",
                 "FLOW_QUERY", "STOCK_LOOKUP", "NEWS_QUERY", "PORTFOLIO_AWARE", "AD_HOC")
        if result in valid:
            return result
        if result.startswith("SIGNAL_DEF:"):
            return result
        return "AD_HOC"
    except Exception:
        return "AD_HOC"


def _build_signal_definition(name: str) -> Optional[str]:
    """Build signal definition narrative."""
    import yaml
    from pathlib import Path
    try:
        cfg_path = Path(__file__).resolve().parents[3] / "config" / "signal_registry.yaml"
        with open(cfg_path) as f:
            registry = yaml.safe_load(f).get("signals", {})
        sig = registry.get(name)
        if sig:
            return (
                f"**{sig['name']}** ({name})\n\n"
                f"{sig.get('description', '')}\n\n"
                f"- **Dashboard page:** {sig.get('page', 'N/A')}"
            )
    except Exception:
        pass
    return None


def _build_signal_overview() -> str:
    """Build overview of all tracked signals."""
    import yaml
    from pathlib import Path
    try:
        cfg_path = Path(__file__).resolve().parents[3] / "config" / "signal_registry.yaml"
        with open(cfg_path) as f:
            registry = yaml.safe_load(f).get("signals", {})
        lines = [f"- **{v['name']}** ({k}): {v.get('description', '')[:80]}" for k, v in registry.items()]
        return (
            "**Signals tracked** by AlphaStream India:\n\n"
            + "\n".join(lines)
            + "\n\nAsk about any specific signal for details."
        )
    except Exception:
        return "AlphaStream tracks 9 signal types across technical, filing, insider, and flow categories."


# ── Analytics queries for standard intents ───────────────────────────────────

_INTENT_SQL = {
    "SIGNAL_QUERY": "SELECT * FROM v_signal_summary WHERE signal_date >= current_date - INTERVAL '7 days' ORDER BY alpha_score DESC LIMIT 20",
    "INSIDER_QUERY": "SELECT * FROM v_insider_activity_30d ORDER BY trade_date DESC LIMIT 20",
    "FLOW_QUERY": "SELECT * FROM v_fii_dii_trend ORDER BY date DESC LIMIT 20",
    "STOCK_LOOKUP": "SELECT * FROM v_stock_screener ORDER BY ticker LIMIT 50",
    "NEWS_QUERY": "SELECT * FROM v_recent_news ORDER BY published_at DESC LIMIT 20",
}


def router_node(
    state: AgentState, *, store: BaseStore
) -> Command[Literal["analytics", "text2sql", "narrate"]]:
    """Unified query classifier and router."""
    query = state.get("query", "")
    session_id = state.get("session_id", "default")
    thought_steps: list[dict] = []

    classification = _classify_query(query)
    thought_steps.append({
        "node": "Router",
        "action": "classify",
        "detail": f"intent → {classification}",
    })

    def _base_update(**overrides):
        base = {
            "thought_steps": thought_steps,
            "_matched_signal": None,
            "_signal_definition": None,
            "error": None,
            "result": None,
            "sql": None,
            "narrative": None,
            "chart_spec": None,
            "sources": None,
            "confidence": None,
            "suggested_questions": None,
        }
        base.update(overrides)
        return base

    # GREETING
    if classification == "GREETING":
        greeting = (
            "Hi! I'm AlphaStream India — your AI-powered market intelligence assistant.\n\n"
            "I can help you with:\n"
            "- **Signal detection**: RSI divergence, MACD crossovers, Bollinger breakouts\n"
            "- **Insider activity**: Who's buying/selling (SAST/PIT data)\n"
            "- **FII/DII flows**: Institutional money movement\n"
            "- **Corporate filings**: Material BSE/NSE announcements\n"
            "- **Portfolio analysis**: Impact on your holdings\n\n"
            "Try asking:\n"
            '- "What signals fired today?"\n'
            '- "Show insider buying in IT sector"\n'
            '- "What are FIIs doing this week?"'
        )
        return Command(update=_base_update(intent="greeting", narrative=greeting), goto="narrate")

    # OFF_TOPIC
    if classification == "OFF_TOPIC":
        return Command(
            update=_base_update(intent="off_topic", error="off-topic", narrative=_OFF_TOPIC_NARRATIVE),
            goto="narrate",
        )

    # SIGNAL_DEF:<NAME>
    if classification.startswith("SIGNAL_DEF:"):
        name = classification.split(":", 1)[1].strip()
        sig_def = _build_signal_definition(name)
        if sig_def:
            return Command(
                update=_base_update(intent="signal_definition", _signal_definition=sig_def),
                goto="narrate",
            )
        # Fall through to AD_HOC

    # Standard intent queries (SIGNAL_QUERY, INSIDER_QUERY, FLOW_QUERY, STOCK_LOOKUP)
    if classification in _INTENT_SQL:
        return Command(
            update=_base_update(intent=classification.lower(), _matched_signal=classification),
            goto="analytics",
        )

    # PORTFOLIO_AWARE → text2sql with portfolio context
    if classification == "PORTFOLIO_AWARE":
        return Command(update=_base_update(intent="portfolio_aware"), goto="text2sql")

    # AD_HOC → text2sql
    return Command(update=_base_update(intent="ad_hoc"), goto="text2sql")


# ── Analytics node ───────────────────────────────────────────────────────────

async def analytics_node(
    state: AgentState,
) -> Command[Literal["narrate"]]:
    """Standard query path — executes pre-defined SQL for known intents."""
    thought_steps = list(state.get("thought_steps", []))
    matched = state.get("_matched_signal", "")

    sql = _INTENT_SQL.get(matched, "")
    if not sql:
        return Command(
            update={**state, "error": "No query matched", "thought_steps": thought_steps},
            goto="narrate",
        )

    result, error = _execute_sql(sql)
    thought_steps.append({
        "node": "Analytics",
        "action": "execute",
        "detail": f"intent={matched}, rows={len(result) if result else 0}, error={error}",
    })

    sources = [f"[Source: AlphaStream {matched.replace('_', ' ').title()} View]"]

    return Command(
        update={**state, "sql": sql, "result": result, "error": error,
                "thought_steps": thought_steps, "sources": sources},
        goto="narrate",
    )


# ── Text2SQL node ────────────────────────────────────────────────────────────

def text2sql_node(state: AgentState) -> AgentState:
    """Ad-hoc query path — full Text2SQL pipeline."""
    query = state.get("query", "")
    history = state.get("history", [])
    thought_steps = list(state.get("thought_steps", []))

    # Build history context
    history_context = ""
    if history:
        recent = history[-3:]
        history_context = (
            "Prior conversation:\n"
            + "\n".join(f"Q: {h['query']}\nA: {h.get('answer', '')[:120]}" for h in recent)
            + "\n\nCurrent question:"
        )
    contextual_query = f"{history_context} {query}" if history_context else query

    try:
        from src.agents.nlq.text2sql.schema_linker import link_schema
        from src.agents.nlq.text2sql.query_planner import plan_query
        from src.agents.nlq.text2sql.sql_generator import generate_sql
        from src.agents.nlq.text2sql.guardrails import check_all
        from src.agents.nlq.text2sql.correction_loop import run_correction_loop

        # Step 1: Schema linking
        schema_link = link_schema(contextual_query)
        thought_steps.append({
            "node": "Text2SQL", "action": "schema_link",
            "detail": f"Linked columns: {list(schema_link.columns.keys())}",
        })

        # Step 2: Query planning
        query_plan = plan_query(query, schema_link)
        thought_steps.append({
            "node": "Text2SQL", "action": "query_plan",
            "detail": f"strategy={query_plan.aggregation_strategy}, tables={query_plan.tables_used}",
        })

        # Step 3: SQL generation
        generated = generate_sql(query, query_plan)
        thought_steps.append({
            "node": "Text2SQL", "action": "sql_gen",
            "detail": f"confidence={generated.confidence:.2f}, sql_len={len(generated.sql)}",
        })

        sql = generated.sql

        # Step 4: Guardrails
        guardrail_result = check_all(sql)
        initial_violations = None
        if not guardrail_result.safe:
            initial_violations = guardrail_result.violations
            thought_steps.append({
                "node": "Text2SQL", "action": "guardrails_fail",
                "detail": f"primary={guardrail_result.primary_category}",
            })
            if guardrail_result.primary_category == "syntax":
                return {**state, "sql": sql, "error": "Guardrails blocked query", "thought_steps": thought_steps}
        else:
            thought_steps.append({"node": "Text2SQL", "action": "guardrails_pass", "detail": "All checks passed"})

        # Step 5: Correction loop
        final_sql, result, error, correction_log = run_correction_loop(
            query, sql, _execute_sql, initial_violations=initial_violations
        )
        if correction_log:
            thought_steps.append({
                "node": "Text2SQL", "action": "correction_loop",
                "detail": " | ".join(correction_log),
            })

        thought_steps.append({
            "node": "Text2SQL", "action": "execute",
            "detail": f"rows={len(result) if result else 0}, error={error}",
        })

        # Search enrichment: if few results, auto-search web
        web_context = None
        try:
            from src.agents.search_agent import get_search_agent
            sa = get_search_agent()
            enrichment = sa.enrich_context(query, len(result) if result else 0)
            if enrichment.get("enriched"):
                web_context = enrichment["summary"]
                thought_steps.append({
                    "node": "Text2SQL", "action": "search_enrich",
                    "detail": f"Web search added {enrichment['source_count']} sources (DB had <5 rows)",
                })
        except Exception:
            pass

        return {**state, "sql": final_sql, "result": result, "error": error,
                "thought_steps": thought_steps,
                "web_search_results": web_context, "search_enriched": bool(web_context)}

    except ImportError:
        # Text2SQL pipeline not yet built — fallback to simple query
        thought_steps.append({
            "node": "Text2SQL", "action": "fallback",
            "detail": "Text2SQL pipeline not available, using simple query",
        })
        # Try a simple keyword-based query
        sql = _simple_query_fallback(query)
        if sql:
            result, error = _execute_sql(sql)
            return {**state, "sql": sql, "result": result, "error": error, "thought_steps": thought_steps}
        return {**state, "error": "Text2SQL pipeline not yet available", "thought_steps": thought_steps}


def _simple_query_fallback(query: str) -> Optional[str]:
    """Simple keyword-based SQL fallback when Text2SQL isn't built yet."""
    q = query.lower()
    if any(w in q for w in ("signal", "opportunity", "alpha", "bullish", "bearish")):
        return "SELECT * FROM v_signal_summary ORDER BY alpha_score DESC LIMIT 20"
    if any(w in q for w in ("insider", "promoter", "bought", "sold", "sast")):
        return "SELECT * FROM v_insider_activity_30d ORDER BY trade_date DESC LIMIT 20"
    if any(w in q for w in ("fii", "dii", "institutional", "foreign")):
        return "SELECT * FROM v_fii_dii_trend ORDER BY date DESC LIMIT 20"
    if any(w in q for w in ("sector", "heatmap")):
        return "SELECT * FROM v_sector_heatmap"
    if any(w in q for w in ("stock", "screener", "price")):
        return "SELECT * FROM v_stock_screener LIMIT 20"
    return None


# ── Narrate node ─────────────────────────────────────────────────────────────

_NARRATE_SYSTEM = (
    "You are AlphaStream India, an AI-powered investment intelligence assistant for Indian stock markets.\n"
    "NEVER reveal internal implementation details or technology names.\n"
    "CRITICAL: ONLY use data provided in the Data sample. NEVER invent numbers.\n"
    "If the data doesn't answer the question, say so.\n"
    "Always cite sources: [Source: NSE SAST Data], [Source: NSDL FII/DII], [Source: BSE Filing], etc.\n"
    "Use ₹ for Indian Rupees. Use Cr for Crores, L for Lakhs.\n"
    "Be specific with numbers. Write concise insights in markdown.\n"
    "After your answer, suggest 3 follow-up questions the user might want to ask.\n"
)


def narrate_node(state: AgentState) -> AgentState:
    """Generate financial narrative with source citations and follow-up suggestions."""
    query = state.get("query", "")
    result = state.get("result")
    error = state.get("error")
    sql = state.get("sql", "")
    thought_steps = list(state.get("thought_steps", []))
    history = list(state.get("history", []))

    # Pre-set definition
    pre_narrative = state.get("_signal_definition")
    if pre_narrative and not result and not error:
        history.append({"query": query, "answer": pre_narrative, "sql": ""})
        return {**state, "narrative": pre_narrative, "thought_steps": thought_steps, "history": history[-20:]}

    # Pre-set narrative (greeting, off-topic, guardrail block)
    existing = state.get("narrative")
    intent = state.get("intent", "")
    if existing and (error or intent in ("off_topic", "greeting")) and not result:
        history.append({"query": query, "answer": existing, "sql": sql or ""})
        return {**state, "narrative": existing, "thought_steps": thought_steps, "history": history[-20:]}

    if error and not result:
        narrative = f"I couldn't find data for that query. {error}"
        history.append({"query": query, "answer": narrative, "sql": sql or ""})
        return {**state, "narrative": narrative, "thought_steps": thought_steps, "history": history[-20:]}

    if not result:
        narrative = "No data found for that query. Try rephrasing or asking about a specific stock, signal, or metric."
        history.append({"query": query, "answer": narrative, "sql": sql or ""})
        return {**state, "narrative": narrative, "thought_steps": thought_steps, "history": history[-20:]}

    # Generate narrative via LLM
    web_context = state.get("web_search_results")
    narrative, chart_spec, suggested = _generate_financial_narrative(query, result, sql, history, web_context)

    thought_steps.append({
        "node": "Narrate", "action": "narrate",
        "detail": f"narrative_len={len(narrative)}, chart_type={chart_spec.get('type', 'none')}",
    })

    history.append({"query": query, "answer": narrative, "sql": sql or ""})
    return {
        **state,
        "narrative": narrative,
        "chart_spec": chart_spec,
        "suggested_questions": suggested,
        "thought_steps": thought_steps,
        "history": history[-20:],
    }


def _generate_financial_narrative(
    query: str, result: list[dict], sql: str, history: list[dict],
    web_context: str = None,
) -> tuple[str, dict, list[str]]:
    """Generate narrative + chart spec + follow-up questions."""
    data = result
    first = data[0] if data else {}
    all_keys = [k for k in first.keys() if not k.startswith("__")]

    try:
        from src.agents.nlq.llm_provider import complete

        sample = json.dumps(data[:5], default=str)
        history_context = ""
        if history:
            recent = history[-2:]
            history_context = "\nPrevious context:\n" + "\n".join(
                f"Q: {h['query']}\nA: {h.get('answer', '')[:200]}" for h in recent
            ) + "\n"

        prompt = (
            f"{_NARRATE_SYSTEM}\n"
            f"Question: {query}\n"
            f"{history_context}"
            f"Data columns: {all_keys}\n"
            f"Data sample (first 5 rows):\n{sample}\n"
            f"Total rows: {len(data)}\n\n"
            "Respond in EXACTLY this format:\n\n"
            "2-4 sentence insight in markdown. Use **bold** for key numbers. Cite sources.\n"
            "---CHART---\n"
            "CHART_TYPE|X_COLUMN|Y_COLUMN\n"
            "---FOLLOWUP---\n"
            "Question 1?\n"
            "Question 2?\n"
            "Question 3?\n\n"
            "CHART_TYPE: number|bar|line|table|donut\n"
        )
        raw = complete(prompt, max_tokens=512)

        # Parse response
        narrative = raw.strip()
        chart_spec = {"type": "table", "data": data[:50]}
        suggested = []

        if "---CHART---" in raw:
            parts = raw.split("---CHART---", 1)
            narrative = parts[0].strip()
            remainder = parts[1].strip() if len(parts) > 1 else ""

            if "---FOLLOWUP---" in remainder:
                chart_part, followup_part = remainder.split("---FOLLOWUP---", 1)
                chart_line = chart_part.strip().split("\n")[0].strip()
                suggested = [q.strip() for q in followup_part.strip().split("\n") if q.strip() and q.strip().endswith("?")][:3]
            else:
                chart_line = remainder.split("\n")[0].strip()

            chart_spec = _parse_chart_line(chart_line, data)

        return narrative, chart_spec, suggested

    except Exception as e:
        narrative = f"Found {len(data)} result(s) for your query."
        chart_spec = _infer_chart_heuristic(data)
        return narrative, chart_spec, []


def _parse_chart_line(chart_line: str, data: list[dict]) -> dict:
    """Parse 'bar|ticker|alpha_score' into chart_spec dict."""
    if not chart_line or "|" not in chart_line:
        return _infer_chart_heuristic(data)
    parts = [p.strip() for p in chart_line.split("|")]
    if len(parts) < 3:
        return _infer_chart_heuristic(data)

    chart_type, x_col, y_col = parts[0].lower(), parts[1], parts[2]
    if chart_type not in ("number", "donut", "line", "bar", "table"):
        chart_type = "bar"

    first = data[0] if data else {}
    all_keys = list(first.keys())
    if x_col not in all_keys:
        x_col = all_keys[0] if all_keys else ""
    if y_col not in all_keys:
        y_col = next((k for k in all_keys if isinstance(first.get(k), (int, float))), all_keys[-1] if all_keys else "")

    if chart_type == "number":
        return {"type": "number", "label": y_col.replace("_", " ").title(), "value": first.get(y_col, 0), "data": data[:1]}
    if chart_type == "donut":
        return {"type": "donut", "x": x_col, "y": y_col, "data": data[:10]}
    if chart_type == "line":
        return {"type": "line", "x": x_col, "y": [y_col], "data": data[:100]}
    if chart_type == "table":
        return {"type": "table", "data": data[:50]}
    return {"type": "bar", "x": x_col, "y": [y_col], "data": data[:50]}


def _infer_chart_heuristic(data: list[dict]) -> dict:
    """Heuristic fallback for chart type."""
    if not data:
        return {"type": "none"}
    first = data[0]
    keys = [k for k in first.keys() if not k.startswith("__")]
    str_keys = [k for k in keys if isinstance(first.get(k), str)]
    num_keys = [k for k in keys if isinstance(first.get(k), (int, float))]
    if str_keys and num_keys and len(data) > 1:
        return {"type": "bar", "x": str_keys[0], "y": num_keys[:3], "data": data[:50]}
    if num_keys and len(data) == 1:
        return {"type": "number", "label": num_keys[0].replace("_", " ").title(), "value": first[num_keys[0]], "data": data}
    return {"type": "table", "data": data[:50]}


# ── Graph assembly ───────────────────────────────────────────────────────────

def _build_graph() -> StateGraph:
    builder = StateGraph(AgentState)

    builder.add_node("input_guardrail", input_guardrail_node)
    builder.add_node("router", router_node)
    builder.add_node("analytics", analytics_node)
    builder.add_node("text2sql", text2sql_node)
    builder.add_node("narrate", narrate_node)
    builder.add_node("output_guardrail", output_guardrail_node)

    builder.add_edge(START, "input_guardrail")
    builder.add_conditional_edges(
        "input_guardrail",
        lambda state: "narrate" if state.get("error") else "router",
        {"narrate": "narrate", "router": "router"},
    )
    # Router uses Command → analytics, text2sql, or narrate
    builder.add_edge("text2sql", "narrate")
    builder.add_edge("narrate", "output_guardrail")
    builder.add_edge("output_guardrail", END)

    return builder


_checkpointer = InMemorySaver()
_graph = _build_graph().compile(checkpointer=_checkpointer, store=_store)


# ── SSE Streaming entry point ────────────────────────────────────────────────

async def stream_qna_agent(
    query: str,
    session_id: str = "default",
    filters: dict | None = None,
    portfolio_context: str | None = None,
) -> AsyncGenerator[dict, None]:
    """Streaming entry point — yields SSE event dicts as nodes complete."""
    input_state: AgentState = {
        "session_id": session_id,
        "query": query,
        "filters": filters or {},
        "thought_steps": [],
        "portfolio_context": portfolio_context,
    }
    config = {"configurable": {"thread_id": session_id}}

    emitted_steps = 0
    final_emitted = False

    try:
        async for chunk in _graph.astream(input_state, config=config, stream_mode="updates"):
            for node_name, update in chunk.items():
                if not isinstance(update, dict):
                    continue

                all_steps = update.get("thought_steps", [])
                new_steps = all_steps[emitted_steps:]
                for step in new_steps:
                    yield {"type": "thought_step", "node": node_name, "data": step}
                emitted_steps = len(all_steps)

                if node_name == "text2sql" and update.get("sql"):
                    yield {"type": "sql_ready", "data": update["sql"]}

                if node_name == "output_guardrail" and update.get("narrative") and not final_emitted:
                    final_emitted = True
                    yield {
                        "type": "final",
                        "answer": update["narrative"],
                        "sql": update.get("sql"),
                        "chart_spec": update.get("chart_spec"),
                        "suggested_questions": update.get("suggested_questions"),
                        "sources": update.get("sources"),
                        "thought_steps": update.get("thought_steps", []),
                    }
    except Exception as e:
        yield {"type": "error", "message": str(e)}


# ── Blocking entry point ─────────────────────────────────────────────────────

async def run_qna_agent(
    query: str,
    session_id: str = "default",
    filters: dict | None = None,
    portfolio_context: str | None = None,
) -> dict[str, Any]:
    """Main entry point — blocking until graph completes."""
    input_state: AgentState = {
        "session_id": session_id,
        "query": query,
        "filters": filters or {},
        "thought_steps": [],
        "portfolio_context": portfolio_context,
    }
    config = {"configurable": {"thread_id": session_id}}
    return await _graph.ainvoke(input_state, config=config)
