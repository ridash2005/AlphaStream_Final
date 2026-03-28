"""
Search Agent — DuckDuckGo-powered context enrichment for NLQ.

Cyclic enrichment: user query → search web → enrich context → agent answers better.
Knowledge threshold: if DuckDB has <5 rows, auto-triggers web search.
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        DDGS_AVAILABLE = True
    except ImportError:
        DDGS_AVAILABLE = False
        logger.warning("ddgs/duckduckgo-search not installed")


class SearchAgent:
    """Web search for financial context enrichment."""

    def __init__(self):
        self._ddgs = DDGS() if DDGS_AVAILABLE else None

    def search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """Search the web via DuckDuckGo. Returns [{title, url, snippet}]."""
        if not self._ddgs:
            return []
        try:
            results = self._ddgs.text(
                f"{query} India stock market NSE BSE",
                max_results=max_results,
            )
            return [
                {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
                for r in results
            ]
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")
            return []

    def search_news(self, query: str, max_results: int = 5) -> list[dict]:
        """Search recent news via DuckDuckGo."""
        if not self._ddgs:
            return []
        try:
            results = self._ddgs.news(query, max_results=max_results)
            return [
                {"title": r.get("title", ""), "url": r.get("url", ""),
                 "source": r.get("source", ""), "date": r.get("date", ""),
                 "snippet": r.get("body", "")}
                for r in results
            ]
        except Exception as e:
            logger.warning(f"DuckDuckGo news search failed: {e}")
            return []

    def enrich_context(
        self, user_query: str, db_result_count: int, threshold: int = 5
    ) -> dict[str, Any]:
        """Auto-enrich context when DuckDB results are insufficient."""
        if db_result_count >= threshold:
            return {"enriched": False, "search_results": [], "summary": ""}

        results = self.search(user_query, max_results=5)
        news = self.search_news(user_query, max_results=3)

        all_results = results + news
        if not all_results:
            return {"enriched": False, "search_results": [], "summary": ""}

        summary = self._build_summary(user_query, all_results)
        return {
            "enriched": True,
            "search_results": all_results,
            "summary": summary,
            "source_count": len(all_results),
        }

    def cyclic_search(self, user_query: str, max_rounds: int = 3,
                      knowledge_threshold: int = 3) -> dict[str, Any]:
        """
        Cyclic search — tries multiple reformulated search prompts until
        knowledge threshold is met.

        Round 1: Raw user query
        Round 2: LLM-rewritten query (more specific)
        Round 3: Entity-focused query (extract tickers/sectors, search each)

        Returns combined context from all rounds.
        """
        all_results = []
        search_log = []

        # Round 1: Raw query
        r1 = self.search(user_query, max_results=3)
        all_results.extend(r1)
        search_log.append(f"Round 1 ({user_query[:40]}): {len(r1)} results")

        if len(all_results) >= knowledge_threshold:
            return self._build_cyclic_result(user_query, all_results, search_log)

        # Round 2: Reformulated query (add financial context)
        reformulated = f"{user_query} India NSE stock market analysis financial results"
        r2 = self.search(reformulated, max_results=3)
        # Deduplicate by URL
        existing_urls = {r.get("url") for r in all_results}
        r2_new = [r for r in r2 if r.get("url") not in existing_urls]
        all_results.extend(r2_new)
        search_log.append(f"Round 2 (reformulated): {len(r2_new)} new results")

        if len(all_results) >= knowledge_threshold:
            return self._build_cyclic_result(user_query, all_results, search_log)

        # Round 3: News-specific search
        r3 = self.search_news(user_query, max_results=3)
        existing_urls = {r.get("url") for r in all_results}
        r3_new = [r for r in r3 if r.get("url") not in existing_urls]
        all_results.extend(r3_new)
        search_log.append(f"Round 3 (news): {len(r3_new)} new results")

        return self._build_cyclic_result(user_query, all_results, search_log)

    def _build_cyclic_result(self, query: str, results: list[dict],
                             search_log: list[str]) -> dict[str, Any]:
        return {
            "enriched": len(results) > 0,
            "search_results": results,
            "summary": self._build_summary(query, results),
            "source_count": len(results),
            "search_rounds": len(search_log),
            "search_log": search_log,
        }

    def _build_summary(self, query: str, results: list[dict]) -> str:
        """Build a context summary from search results."""
        snippets = []
        for r in results[:5]:
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            source = r.get("source", r.get("url", ""))
            if snippet:
                snippets.append(f"- {title}: {snippet[:150]} [Source: {source}]")
        return f"Web search results for '{query}':\n" + "\n".join(snippets)

    def generate_enriched_prompt(
        self, original_query: str, search_results: list[dict], db_results: list[dict]
    ) -> str:
        """Combine DB results + web search into enriched context."""
        parts = [f"User question: {original_query}\n"]

        if db_results:
            parts.append(f"Database results ({len(db_results)} rows available).\n")

        if search_results:
            parts.append("Additional web context:\n")
            for r in search_results[:5]:
                parts.append(f"- [{r.get('title', '')}]: {r.get('snippet', '')[:120]}")

        parts.append("\nAnswer using both database data and web context. Cite sources.")
        return "\n".join(parts)


_search_agent = None


def get_search_agent() -> SearchAgent:
    global _search_agent
    if _search_agent is None:
        _search_agent = SearchAgent()
    return _search_agent
