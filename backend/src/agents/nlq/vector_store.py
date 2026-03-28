"""
Vector Store — ChromaDB-based schema similarity search for NLQ.

Embeds table/column descriptions and financial terms.
Used by the router as a fallback for intent classification.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_collection = None
_initialized = False

# Financial schema documents to embed
_SCHEMA_DOCS = [
    {"id": "dim_stocks", "text": "dim_stocks: Stock dimension table with ticker, company_name, sector, industry, market_cap_cr, index_membership (nifty50/nifty100/nifty500)", "type": "table"},
    {"id": "fact_daily_prices", "text": "fact_daily_prices: Daily OHLCV price data for NSE stocks — ticker, date, open, high, low, close, volume", "type": "table"},
    {"id": "fact_signals", "text": "fact_signals: Detected trading signals — signal_type (technical/filing/insider/flow/sentiment), direction (bullish/bearish/neutral), confidence, alpha_score", "type": "table"},
    {"id": "fact_insider_trades", "text": "fact_insider_trades: NSE insider trading data (SAST/PIT) — person_name, person_category (promoter/director/kmp), trade_type (buy/sell), quantity, value_lakhs", "type": "table"},
    {"id": "fact_fii_dii_flows", "text": "fact_fii_dii_flows: FII/DII institutional flow data — fii_buy_cr, fii_sell_cr, fii_net_cr, dii_buy_cr, dii_sell_cr, dii_net_cr", "type": "table"},
    {"id": "fact_filings", "text": "fact_filings: BSE/NSE corporate filings — filing_type (board_meeting/acquisition/debt/expansion), materiality (high/medium/low), sentiment", "type": "table"},
    {"id": "v_signal_summary", "text": "v_signal_summary: Pre-joined view of signals with stock info, ordered by alpha_score — use for signal queries", "type": "view"},
    {"id": "v_insider_activity_30d", "text": "v_insider_activity_30d: Insider trades last 30 days with company info — use for insider buying/selling queries", "type": "view"},
    {"id": "v_fii_dii_trend", "text": "v_fii_dii_trend: FII/DII flows with 5-day and 20-day rolling net sums — use for FII/DII trend queries", "type": "view"},
    {"id": "v_sector_heatmap", "text": "v_sector_heatmap: Sector-wise signal counts and average alpha scores — use for sector comparison", "type": "view"},
    {"id": "v_stock_screener", "text": "v_stock_screener: Latest price and signal per stock — use for stock lookup and screening", "type": "view"},
    # Financial term synonyms
    {"id": "term_fii", "text": "FII: Foreign Institutional Investor — tracks in fact_fii_dii_flows table, columns fii_buy_cr, fii_sell_cr, fii_net_cr", "type": "term"},
    {"id": "term_dii", "text": "DII: Domestic Institutional Investor — tracks in fact_fii_dii_flows table, columns dii_buy_cr, dii_sell_cr, dii_net_cr", "type": "term"},
    {"id": "term_insider", "text": "Insider trading, promoter buying, SAST, PIT — tracks in fact_insider_trades table", "type": "term"},
    {"id": "term_alpha", "text": "Alpha Score, opportunity score, signal strength — alpha_score column in fact_signals (0-100)", "type": "term"},
    {"id": "term_bullish", "text": "Bullish, buy signal, positive — direction='bullish' in fact_signals", "type": "term"},
    {"id": "term_bearish", "text": "Bearish, sell signal, negative — direction='bearish' in fact_signals", "type": "term"},
    {"id": "term_rsi", "text": "RSI, RSI divergence, oversold, overbought — signal_type='technical' AND pattern='rsi_divergence' in fact_signals", "type": "term"},
    {"id": "term_macd", "text": "MACD, MACD crossover — signal_type='technical' AND pattern='macd_crossover' in fact_signals", "type": "term"},
    {"id": "term_nifty50", "text": "Nifty 50, Nifty50, large cap, blue chip — 'nifty50' = ANY(index_membership) in dim_stocks", "type": "term"},
    # Articles/News
    {"id": "fact_articles", "text": "fact_articles: News articles from ET Markets, MoneyControl, LiveMint with title, content, source, tickers mentioned, sentiment (positive/negative/neutral)", "type": "table"},
    {"id": "v_recent_news", "text": "v_recent_news: Recent news headlines with tickers and sentiment — use for news queries", "type": "view"},
    {"id": "term_news", "text": "News, headlines, articles, market updates — query fact_articles or v_recent_news table", "type": "term"},
]

_SIMILARITY_THRESHOLD = 0.3  # ChromaDB default embeddings need lower threshold


def _init_store():
    """Initialize ChromaDB collection with schema documents."""
    global _collection, _initialized
    if _initialized:
        return

    try:
        import chromadb
        client = chromadb.Client()
        _collection = client.get_or_create_collection(
            name="alphastream_schema",
            metadata={"hnsw:space": "cosine"},
        )

        # Only add if empty
        if _collection.count() == 0:
            _collection.add(
                ids=[d["id"] for d in _SCHEMA_DOCS],
                documents=[d["text"] for d in _SCHEMA_DOCS],
                metadatas=[{"type": d["type"]} for d in _SCHEMA_DOCS],
            )
            logger.info(f"Vector store initialized with {len(_SCHEMA_DOCS)} documents")

        _initialized = True
    except Exception as e:
        logger.warning(f"ChromaDB init failed: {e}")
        _initialized = True  # Don't retry


def query_schema_similarity(query: str, n_results: int = 5) -> list[dict]:
    """Find schema elements most similar to the query."""
    _init_store()
    if _collection is None:
        return []

    try:
        results = _collection.query(query_texts=[query], n_results=n_results)
        matches = []
        for i, doc_id in enumerate(results["ids"][0]):
            score = 1 - results["distances"][0][i]  # cosine distance → similarity
            if score >= _SIMILARITY_THRESHOLD:
                matches.append({
                    "id": doc_id,
                    "document": results["documents"][0][i],
                    "score": round(score, 3),
                    "type": results["metadatas"][0][i].get("type", "unknown"),
                })
        return matches
    except Exception as e:
        logger.warning(f"Vector search failed: {e}")
        return []
