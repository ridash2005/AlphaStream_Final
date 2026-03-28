"""
Article ingestion bridge — writes news articles to DuckDB for NLQ querying.

Called from app.py's on_new_article callback and from RSS connector.
"""
import hashlib
import logging
import re
from typing import Any

import duckdb

from src.data.market_schema import get_db_path

logger = logging.getLogger(__name__)

# Common Indian stock tickers to detect in text
_TICKER_PATTERN = re.compile(
    r'\b(RELIANCE|TCS|INFY|INFOSYS|HDFCBANK|HDFC\s*BANK|ICICIBANK|ICICI\s*BANK|'
    r'SBIN|SBI|BHARTIARTL|AIRTEL|ITC|HINDUNILVR|HUL|KOTAKBANK|KOTAK|'
    r'LT|LARSEN|AXISBANK|AXIS\s*BANK|BAJFINANCE|BAJAJ\s*FINANCE|'
    r'ASIANPAINT|ASIAN\s*PAINTS|MARUTI|TITAN|SUNPHARMA|SUN\s*PHARMA|'
    r'TATAMOTORS|TATA\s*MOTORS|WIPRO|HCLTECH|HCL\s*TECH|NTPC|ONGC|'
    r'POWERGRID|TATASTEEL|TATA\s*STEEL|ADANIENT|ADANI|JSWSTEEL|JSW|'
    r'TECHM|TECH\s*MAHINDRA|COALINDIA|COAL\s*INDIA|DRREDDY|CIPLA|'
    r'NESTLEIND|NESTLE|HEROMOTOCO|HERO|APOLLOHOSP|APOLLO|BRITANNIA|'
    r'NIFTY|SENSEX|BSE|NSE|RBI|SEBI|FII|DII|NSDL)\b',
    re.IGNORECASE,
)

# Map common names to ticker symbols
_NAME_TO_TICKER = {
    "infosys": "INFY", "hdfc bank": "HDFCBANK", "icici bank": "ICICIBANK",
    "sbi": "SBIN", "airtel": "BHARTIARTL", "hul": "HINDUNILVR",
    "kotak": "KOTAKBANK", "larsen": "LT", "axis bank": "AXISBANK",
    "bajaj finance": "BAJFINANCE", "asian paints": "ASIANPAINT",
    "sun pharma": "SUNPHARMA", "tata motors": "TATAMOTORS",
    "hcl tech": "HCLTECH", "tata steel": "TATASTEEL", "adani": "ADANIENT",
    "jsw": "JSWSTEEL", "tech mahindra": "TECHM", "coal india": "COALINDIA",
    "nestle": "NESTLEIND", "hero": "HEROMOTOCO", "apollo": "APOLLOHOSP",
}


def ingest_article_to_duckdb(article: dict[str, Any]) -> bool:
    """Write a single article to DuckDB fact_articles table."""
    try:
        article_id = article.get("id") or hashlib.sha256(
            (article.get("title", "") + article.get("url", "")).encode()
        ).hexdigest()[:12]

        title = article.get("title", "")
        description = article.get("description", "")
        content = article.get("content", description)
        source = article.get("source", "Unknown")
        url = article.get("url", "")
        published_at = article.get("published_at", article.get("publishedAt", ""))

        # Extract tickers mentioned
        text = f"{title} {description} {content}"
        raw_matches = set(m.lower().strip() for m in _TICKER_PATTERN.findall(text))
        tickers = list(set(
            _NAME_TO_TICKER.get(m, m.upper()) for m in raw_matches
        ))

        # Simple sentiment from title keywords
        pos_words = {"surge", "jump", "gain", "rally", "rise", "bull", "buy", "upgrade", "profit", "growth"}
        neg_words = {"fall", "drop", "crash", "decline", "loss", "bear", "sell", "downgrade", "slump", "cut"}
        title_lower = title.lower()
        pos = sum(1 for w in pos_words if w in title_lower)
        neg = sum(1 for w in neg_words if w in title_lower)
        sentiment = "positive" if pos > neg else "negative" if neg > pos else "neutral"

        con = duckdb.connect(get_db_path())
        try:
            con.execute("""
                INSERT INTO fact_articles
                (id, title, description, content, source, url, tickers, sentiment, published_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, TRY_CAST(? AS TIMESTAMP))
                ON CONFLICT (id) DO NOTHING
            """, [article_id, title, description, content[:5000], source, url,
                  tickers, sentiment, published_at])
            return True
        finally:
            con.close()

    except Exception as e:
        logger.warning(f"Article ingest to DuckDB failed: {e}")
        return False


def bulk_ingest_articles(articles: list[dict]) -> int:
    """Bulk ingest articles. Returns count of successfully ingested."""
    count = 0
    for article in articles:
        if ingest_article_to_duckdb(article):
            count += 1
    if count:
        logger.info(f"Ingested {count}/{len(articles)} articles to DuckDB")
    return count


def ingest_rss_to_duckdb() -> int:
    """Fetch current RSS feeds and ingest to DuckDB."""
    try:
        from src.connectors.rss_connector import get_rss_connector
        rss = get_rss_connector()
        articles = rss.fetch_articles()
        return bulk_ingest_articles(articles)
    except Exception as e:
        logger.warning(f"RSS → DuckDB ingest failed: {e}")
        return 0
