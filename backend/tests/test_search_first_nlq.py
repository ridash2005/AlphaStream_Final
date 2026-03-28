"""
TDD Tests for Search-First NLQ Pipeline + Persistent Memory.

Run: .venv/bin/python -m pytest tests/test_search_first_nlq.py -v
"""
import asyncio
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS",
    "/home/bakasur/AlphaStream_India/agrowise-192e3-feea2cfd6558.json")


# ── TODO 1: Search agent returns results ──────────────────────────────────

def test_search_agent_returns_results():
    """Search agent should return web results for financial queries."""
    from src.agents.search_agent import get_search_agent
    sa = get_search_agent()
    results = sa.search("Reliance Industries quarterly results", max_results=3)
    assert isinstance(results, list)
    assert len(results) >= 1, "Should find at least 1 web result"
    assert "title" in results[0]
    assert "snippet" in results[0]


def test_search_enrichment_triggers_on_sparse_data():
    """Enrichment should trigger when DB has < threshold rows."""
    from src.agents.search_agent import get_search_agent
    sa = get_search_agent()
    enrichment = sa.enrich_context("Adani quarterly results", db_result_count=0, threshold=5)
    assert enrichment["enriched"] is True
    assert len(enrichment["search_results"]) > 0
    assert "summary" in enrichment


def test_search_enrichment_skips_on_sufficient_data():
    """Enrichment should NOT trigger when DB has enough rows."""
    from src.agents.search_agent import get_search_agent
    sa = get_search_agent()
    enrichment = sa.enrich_context("anything", db_result_count=10, threshold=5)
    assert enrichment["enriched"] is False


# ── TODO 2: Enrichment node runs BEFORE router ───────────────────────────

def test_enrich_node_exists_in_graph():
    """Graph should have an 'enrich' node between input_guardrail and router."""
    from src.agents.nlq.qna_agent import _build_graph
    graph = _build_graph()
    node_names = list(graph.nodes.keys())
    assert "enrich" in node_names, f"'enrich' node missing. Nodes: {node_names}"


def test_enrich_runs_before_router():
    """Enrich node should execute before router in the graph flow."""
    from src.agents.nlq.qna_agent import _build_graph
    graph = _build_graph()
    # Check edge: input_guardrail → enrich (not directly to router)
    node_names = list(graph.nodes.keys())
    enrich_idx = node_names.index("enrich") if "enrich" in node_names else -1
    router_idx = node_names.index("router") if "router" in node_names else -1
    assert enrich_idx < router_idx, "enrich must come before router"


# ── TODO 3: Persistent memory survives restart ───────────────────────────

def test_persistent_memory_write():
    """Memory should persist to DuckDB."""
    from src.agents.nlq.memory import save_memory, load_memory
    save_memory("test_session", "test_key", {"query": "test", "intent": "ad_hoc"})
    loaded = load_memory("test_session", "test_key")
    assert loaded is not None
    assert loaded["query"] == "test"


def test_persistent_memory_survives_reload():
    """Memory written in one call should be readable in another."""
    from src.agents.nlq.memory import save_memory, load_memory
    save_memory("persist_test", "key1", {"value": "persistent"})
    # Simulate restart by re-importing
    from importlib import reload
    import src.agents.nlq.memory as mem_module
    reload(mem_module)
    loaded = mem_module.load_memory("persist_test", "key1")
    assert loaded is not None
    assert loaded["value"] == "persistent"


# ── TODO 4: Full pipeline with enrichment ─────────────────────────────────

@pytest.mark.asyncio
async def test_full_pipeline_with_search_enrichment():
    """Full NLQ pipeline should include search enrichment in thought steps."""
    from src.agents.nlq.qna_agent import run_qna_agent
    result = await run_qna_agent("What happened to Adani stocks recently?")
    assert result.get("narrative"), "Should have a narrative"
    thought_nodes = [s.get("node") for s in result.get("thought_steps", [])]
    # Enrich should appear in thought steps
    assert "Enrich" in thought_nodes or "Router" in thought_nodes, \
        f"Expected Enrich or Router in steps, got: {thought_nodes}"


@pytest.mark.asyncio
async def test_nlq_greeting_still_works():
    """Greeting should still work after adding enrich node."""
    from src.agents.nlq.qna_agent import run_qna_agent
    result = await run_qna_agent("Hello!")
    assert result.get("intent") == "greeting"
    assert "AlphaStream" in result.get("narrative", "")
