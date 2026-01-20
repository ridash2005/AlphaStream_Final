"""
RSS News Connector - Free news fallback using RSS feeds.

Fetches financial news from public RSS feeds when NewsAPI is rate-limited.
No API key required.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any
import hashlib

import requests

logger = logging.getLogger(__name__)

# Public financial news RSS feeds (no API key required)
RSS_FEEDS = [
    {
        "name": "Yahoo Finance",
        "url": "https://finance.yahoo.com/news/rssindex",
        "source": "Yahoo Finance"
    },
    {
        "name": "Reuters Business",
        "url": "https://ir.thomsonreuters.com/rss/news-releases.xml?items=15",
        "source": "Reuters"
    },
    {
        "name": "MarketWatch",
        "url": "https://feeds.marketwatch.com/marketwatch/topstories/",
        "source": "MarketWatch"
    },
    {
        "name": "Seeking Alpha",
        "url": "https://seekingalpha.com/market_currents.xml",
        "source": "Seeking Alpha"
    }
]


class RSSNewsConnector:
    """
    Fallback news connector using public RSS feeds.
    
    Used when NewsAPI hits rate limits (429 errors).
    """
    
    def __init__(self, refresh_interval: int = 30):
        self.refresh_interval = refresh_interval
        self.seen_ids: set[str] = set()
        self.last_fetch: datetime = datetime.min
    
    def fetch_articles(self, query: str = None) -> list[dict[str, Any]]:
        """
        Fetch articles from RSS feeds.
        
        Args:
            query: Optional filter term (e.g., ticker symbol)
            
        Returns:
            List of article dicts
        """
        articles = []
        
        for feed in RSS_FEEDS:
            try:
                feed_articles = self._parse_rss_feed(feed)
                articles.extend(feed_articles)
            except Exception as e:
                logger.debug(f"Error fetching {feed['name']}: {e}")
                continue
        
        # Filter by query if provided
        if query:
            query_lower = query.lower()
            articles = [a for a in articles if query_lower in a.get('content', '').lower() 
                       or query_lower in a.get('title', '').lower()]
        
        # Deduplicate
        unique_articles = []
        for article in articles:
            article_id = self._generate_id(article)
            if article_id not in self.seen_ids:
                self.seen_ids.add(article_id)
                article['id'] = article_id
                unique_articles.append(article)
        
        logger.info(f"RSS connector fetched {len(unique_articles)} new articles")
        return unique_articles
    
    def _parse_rss_feed(self, feed: dict) -> list[dict[str, Any]]:
        """Parse a single RSS feed with timeout."""
        try:
            import feedparser
            
            # Fetch with timeout first, then parse
            try:
                response = requests.get(feed["url"], timeout=3)  # Short timeout
                if response.status_code != 200:
                    return []
                parsed = feedparser.parse(response.content)
            except requests.exceptions.Timeout:
                logger.debug(f"RSS feed timeout: {feed['name']}")
                return []
            except requests.exceptions.RequestException as e:
                logger.debug(f"RSS feed error {feed['name']}: {e}")
                return []
            
            articles = []
            for entry in parsed.entries[:10]:  # Last 10 articles
                articles.append({
                    "title": entry.get("title", ""),
                    "description": entry.get("summary", "")[:500] if entry.get("summary") else "",
                    "content": entry.get("summary", "") or "",
                    "source": feed["source"],
                    "url": entry.get("link", ""),
                    "published_at": entry.get("published", datetime.now().isoformat()),
                    "image_url": ""
                })
            return articles
            
        except ImportError:
            # Simple fallback without feedparser
            return self._simple_rss_parse(feed)
    
    def _simple_rss_parse(self, feed: dict) -> list[dict[str, Any]]:
        """Simple RSS parsing without feedparser."""
        try:
            response = requests.get(feed["url"], timeout=3)  # Short timeout
            response.raise_for_status()
            
            # Very basic XML parsing
            import re
            items = re.findall(r'<item>(.*?)</item>', response.text, re.DOTALL)
            
            articles = []
            for item in items[:10]:
                title = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
                desc = re.search(r'<description>(.*?)</description>', item, re.DOTALL)
                link = re.search(r'<link>(.*?)</link>', item, re.DOTALL)
                
                if title:
                    articles.append({
                        "title": title.group(1).strip(),
                        "description": desc.group(1).strip() if desc else "",
                        "content": desc.group(1).strip() if desc else "",
                        "source": feed["source"],
                        "url": link.group(1).strip() if link else "",
                        "published_at": datetime.now().isoformat(),
                        "image_url": ""
                    })
            return articles
            
        except Exception as e:
            logger.debug(f"Simple RSS parse error: {e}")
            return []
    
    def _generate_id(self, article: dict) -> str:
        """Generate unique ID for article."""
        content = f"{article.get('title', '')}{article.get('url', '')}"
        return hashlib.md5(content.encode()).hexdigest()


# Singleton
_rss_connector: RSSNewsConnector | None = None


def get_rss_connector() -> RSSNewsConnector:
    """Get or create RSS connector singleton."""
    global _rss_connector
    if _rss_connector is None:
        _rss_connector = RSSNewsConnector()
    return _rss_connector
