"""
Custom Pathway connector for NewsAPI.org.

This connector polls NewsAPI every N seconds and streams new articles
into the Pathway pipeline for real-time processing.
"""

import hashlib
import logging
import time
from datetime import datetime, timedelta
from typing import Any

import pathway as pw
import requests

from src.config import get_settings

logger = logging.getLogger(__name__)


class NewsArticleSchema(pw.Schema):
    """Schema for news articles."""

    id: str = pw.column_definition(primary_key=True)
    title: str
    description: str
    content: str
    source: str
    url: str
    published_at: str
    image_url: str


class NewsAPISubject(pw.io.python.ConnectorSubject):
    """
    Pathway ConnectorSubject for NewsAPI.org streaming.
    
    Polls the API at configured intervals and pushes new articles
    to the Pathway table. Implements deduplication to avoid
    processing the same article twice.
    """

    def __init__(
        self,
        api_key: str,
        query: str = "stock market OR earnings OR trading",
        refresh_interval: int = 30,
    ):
        super().__init__()
        self.api_key = api_key
        self.query = query
        self.refresh_interval = refresh_interval
        self.seen_ids: set[str] = set()
        self._running = True

    def run(self) -> None:
        """Main loop - uses Herd of Knowledge aggregator for articles."""
        logger.info(f"📰 Starting Herd of Knowledge connector with {self.refresh_interval}s interval")

        while self._running:
            try:
                # PRIMARY ENGINE: Use news aggregator (all sources in parallel)
                articles = self._fetch_from_herd()
                new_count = 0

                for article in articles:
                    article_id = self._generate_id(article)

                    if article_id not in self.seen_ids:
                        self.seen_ids.add(article_id)
                        self._push_article(article_id, article)
                        new_count += 1

                if new_count > 0:
                    logger.info(f"📥 Ingested {new_count} new articles from Herd of Knowledge")

                # Commit the batch
                self._commit()

            except Exception as e:
                logger.error(f"Error in Herd of Knowledge: {e}")

            time.sleep(self.refresh_interval)
    
    def _fetch_from_herd(self) -> list[dict[str, Any]]:
        """PRIMARY: Fetch from all sources via news aggregator."""
        try:
            from src.connectors.news_aggregator import get_news_aggregator
            aggregator = get_news_aggregator()
            return aggregator.fetch_all(self.query)
        except Exception as e:
            logger.error(f"News aggregator error: {e}")
            return []

    def on_stop(self) -> None:
        """Called when the connector is stopped."""
        self._running = False
        logger.info("NewsAPI connector stopped")

    def _fetch_articles(self) -> list[dict[str, Any]]:
        """Fetch articles from NewsAPI, fallback to RSS on rate limit."""
        # Get articles from last 24 hours
        from_date = (datetime.utcnow() - timedelta(hours=24)).isoformat()

        params = {
            "q": self.query,
            "sortBy": "publishedAt",
            "pageSize": 100,
            "apiKey": self.api_key,
            "from": from_date,
            "language": "en",
        }

        response = requests.get(
            "https://newsapi.org/v2/everything",
            params=params,
            timeout=30,
        )

        if response.status_code == 429:
            # Rate limited - fallback to RSS
            logger.warning("NewsAPI rate limited (429). Using RSS fallback.")
            return self._fetch_from_rss()
        
        if response.status_code != 200:
            logger.warning(f"NewsAPI returned status {response.status_code}")
            return self._fetch_from_rss()

        data = response.json()
        return data.get("articles", [])
    
    def _fetch_from_rss(self) -> list[dict[str, Any]]:
        """Fallback to news aggregator when NewsAPI is unavailable."""
        try:
            # First try the full aggregator (Finnhub, Alpha Vantage, MediaStack, RSS)
            from src.connectors.news_aggregator import get_news_aggregator
            aggregator = get_news_aggregator()
            articles = aggregator.fetch_all(self.query)
            if articles:
                logger.info(f"News aggregator provided {len(articles)} articles")
                return articles
        except Exception as e:
            logger.warning(f"News aggregator error: {e}")
        
        # Pure RSS fallback
        try:
            from src.connectors.rss_connector import get_rss_connector
            rss = get_rss_connector()
            articles = rss.fetch_articles()
            # Convert to NewsAPI format
            return [{
                "title": a.get("title", ""),
                "description": a.get("description", ""),
                "content": a.get("content", ""),
                "source": {"name": a.get("source", "RSS")},
                "url": a.get("url", ""),
                "publishedAt": a.get("published_at", ""),
                "urlToImage": a.get("image_url", "")
            } for a in articles]
        except Exception as e:
            logger.error(f"RSS fallback error: {e}")
            return []

    def _generate_id(self, article: dict[str, Any]) -> str:
        """Generate unique ID for article based on content hash."""
        content = f"{article.get('title', '')}{article.get('url', '')}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _push_article(self, article_id: str, article: dict[str, Any]) -> None:
        """Push article to Pathway table."""
        source = article.get("source", {})
        source_name = source.get("name", "Unknown") if isinstance(source, dict) else str(source)

        self.next(
            id=article_id,
            title=article.get("title", ""),
            description=article.get("description", "") or "",
            content=article.get("content", "") or article.get("description", "") or "",
            source=source_name,
            url=article.get("url", ""),
            published_at=article.get("publishedAt", ""),
            image_url=article.get("urlToImage", "") or "",
        )

    def _commit(self) -> None:
        """Commit the current batch of articles."""
        # This signals Pathway to process the batch
        pass


def create_news_table(
    api_key: str | None = None,
    query: str = "stock market OR earnings OR trading",
    refresh_interval: int | None = None,
) -> pw.Table:
    """
    Create a Pathway table streaming news articles.

    Args:
        api_key: NewsAPI key (defaults to config)
        query: Search query for articles
        refresh_interval: Polling interval in seconds (defaults to config)

    Returns:
        Pathway Table with streaming articles
    """
    settings = get_settings()

    if api_key is None:
        api_key = settings.newsapi_key
    if refresh_interval is None:
        refresh_interval = settings.refresh_interval

    subject = NewsAPISubject(
        api_key=api_key,
        query=query,
        refresh_interval=refresh_interval,
    )

    table = pw.io.python.read(
        subject,
        schema=NewsArticleSchema,
    )

    logger.info("News table created and ready for streaming")
    return table


# For testing: create a demo data source
def create_demo_news_table() -> pw.Table:
    """
    Create a demo news table with sample data for testing.
    Uses Pathway's demo module for simulated streaming.
    """
    sample_data = [
        {
            "id": "demo1",
            "title": "Apple Reports Record Q4 Earnings",
            "description": "Apple Inc. reported record quarterly earnings...",
            "content": "Apple Inc. reported record quarterly earnings, beating analyst expectations with strong iPhone sales.",
            "source": "Reuters",
            "url": "https://example.com/apple-earnings",
            "published_at": datetime.utcnow().isoformat(),
            "image_url": "",
        },
        {
            "id": "demo2",
            "title": "Microsoft Cloud Revenue Surges",
            "description": "Microsoft Azure sees 30% growth...",
            "content": "Microsoft's cloud computing division Azure saw 30% year-over-year growth in Q4.",
            "source": "CNBC",
            "url": "https://example.com/msft-cloud",
            "published_at": datetime.utcnow().isoformat(),
            "image_url": "",
        },
        {
            "id": "demo3",
            "title": "Tesla Stock Drops on Delivery Miss",
            "description": "Tesla shares fell 5% after...",
            "content": "Tesla shares fell 5% after the company reported deliveries below analyst expectations.",
            "source": "Bloomberg",
            "url": "https://example.com/tsla-drop",
            "published_at": datetime.utcnow().isoformat(),
            "image_url": "",
        },
    ]

    return pw.debug.table_from_rows(
        schema=NewsArticleSchema,
        rows=[
            (
                d["id"],
                d["title"],
                d["description"],
                d["content"],
                d["source"],
                d["url"],
                d["published_at"],
                d["image_url"],
            )
            for d in sample_data
        ],
    )
