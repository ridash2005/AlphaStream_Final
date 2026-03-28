"""
Search MCP Server — DuckDuckGo web search for NLQ context enrichment.
"""
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from fastmcp import FastMCP

mcp = FastMCP("search_server")


@mcp.tool()
def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web for financial information via DuckDuckGo."""
    from src.agents.search_agent import get_search_agent
    sa = get_search_agent()
    return sa.search(query, max_results=max_results)


@mcp.tool()
def news_search(query: str, max_results: int = 5) -> list[dict]:
    """Search recent news articles via DuckDuckGo."""
    from src.agents.search_agent import get_search_agent
    sa = get_search_agent()
    return sa.search_news(query, max_results=max_results)


@mcp.tool()
def search_and_enrich(query: str, db_result_count: int = 0) -> dict:
    """Search web and generate enriched context for NLQ agent."""
    from src.agents.search_agent import get_search_agent
    sa = get_search_agent()
    return sa.enrich_context(query, db_result_count, threshold=5)


if __name__ == "__main__":
    mcp.run()
