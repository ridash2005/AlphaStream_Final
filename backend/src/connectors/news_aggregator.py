"""
Multi-Source News Aggregator - Combines multiple free news APIs.

Provides fallback across multiple news sources:
- NewsAPI.org (primary - rate limited)
- Finnhub (60 calls/min free)
- Alpha Vantage News (500 calls/day free)
- MediaStack (500 calls/month free)
- RSS Feeds (unlimited, free)
"""

import logging
import time
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional
from abc import ABC, abstractmethod

import requests

from src.config import get_settings

logger = logging.getLogger(__name__)


class NewsSource(ABC):
    """Abstract base class for news sources."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def fetch(self, query: str = None) -> list[dict[str, Any]]:
        """Fetch articles, return in standard format."""
        pass
    
    def normalize_article(self, article: dict) -> dict[str, Any]:
        """Convert to standard article format."""
        return {
            "title": article.get("title", ""),
            "description": article.get("description", "")[:500] if article.get("description") else "",
            "content": article.get("content", "") or article.get("description", ""),
            "source": article.get("source", self.name),
            "url": article.get("url", ""),
            "publishedAt": article.get("publishedAt", datetime.now().isoformat()),
            "urlToImage": article.get("urlToImage", "")
        }


class FinnhubSource(NewsSource):
    """
    Finnhub.io news API.
    Free tier: 60 calls/minute.
    """
    
    name = "Finnhub"
    BASE_URL = "https://finnhub.io/api/v1"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or get_settings().finnhub_api_key
        self.last_call = 0
        self.min_interval = 1.0  # 1 second between calls for safety
    
    def fetch(self, query: str = None) -> list[dict[str, Any]]:
        if not self.api_key:
            logger.debug("Finnhub API key not configured")
            return []
        
        # Rate limiting
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        
        try:
            # Finnhub requires a symbol for company news
            symbol = query.upper() if query else "AAPL"
            
            # Get company news
            response = requests.get(
                f"{self.BASE_URL}/company-news",
                params={
                    "symbol": symbol,
                    "from": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                    "to": datetime.now().strftime("%Y-%m-%d"),
                    "token": self.api_key
                },
                timeout=10
            )
            self.last_call = time.time()
            
            if response.status_code != 200:
                logger.warning(f"Finnhub returned {response.status_code}")
                return []
            
            articles = response.json()
            return [self._convert(a) for a in articles[:20]]
            
        except Exception as e:
            logger.error(f"Finnhub error: {e}")
            return []
    
    def _convert(self, article: dict) -> dict[str, Any]:
        """Convert Finnhub format to standard format."""
        return {
            "title": article.get("headline", ""),
            "description": article.get("summary", "")[:500],
            "content": article.get("summary", ""),
            "source": {"name": article.get("source", "Finnhub")},
            "url": article.get("url", ""),
            "publishedAt": datetime.fromtimestamp(article.get("datetime", 0)).isoformat(),
            "urlToImage": article.get("image", "")
        }


class AlphaVantageSource(NewsSource):
    """
    Alpha Vantage News API.
    Free tier: 500 calls/day.
    """
    
    name = "AlphaVantage"
    BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or get_settings().alphavantage_api_key
    
    def fetch(self, query: str = None) -> list[dict[str, Any]]:
        if not self.api_key:
            logger.debug("Alpha Vantage API key not configured")
            return []
        
        try:
            # Use NEWS_SENTIMENT endpoint
            tickers = query.upper() if query else "AAPL"
            
            response = requests.get(
                self.BASE_URL,
                params={
                    "function": "NEWS_SENTIMENT",
                    "tickers": tickers,
                    "apikey": self.api_key,
                    "limit": 50
                },
                timeout=15
            )
            
            if response.status_code != 200:
                logger.warning(f"Alpha Vantage returned {response.status_code}")
                return []
            
            data = response.json()
            
            # Check for rate limit message
            if "Note" in data or "Information" in data:
                logger.warning("Alpha Vantage rate limited")
                return []
            
            articles = data.get("feed", [])
            return [self._convert(a) for a in articles[:20]]
            
        except Exception as e:
            logger.error(f"Alpha Vantage error: {e}")
            return []
    
    def _convert(self, article: dict) -> dict[str, Any]:
        """Convert Alpha Vantage format to standard format."""
        return {
            "title": article.get("title", ""),
            "description": article.get("summary", "")[:500],
            "content": article.get("summary", ""),
            "source": {"name": article.get("source", "Alpha Vantage")},
            "url": article.get("url", ""),
            "publishedAt": article.get("time_published", ""),
            "urlToImage": article.get("banner_image", "")
        }


class MediaStackSource(NewsSource):
    """
    MediaStack news API.
    Free tier: 500 calls/month.
    """
    
    name = "MediaStack"
    BASE_URL = "http://api.mediastack.com/v1/news"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or get_settings().mediastack_api_key
        self._call_count = 0
        self._max_calls = 500  # Monthly limit
    
    def fetch(self, query: str = None) -> list[dict[str, Any]]:
        if not self.api_key:
            logger.debug("MediaStack API key not configured")
            return []
        
        if self._call_count >= self._max_calls:
            logger.warning("MediaStack monthly limit reached")
            return []
        
        try:
            keywords = query if query else "stock market finance trading"
            
            response = requests.get(
                self.BASE_URL,
                params={
                    "access_key": self.api_key,
                    "keywords": keywords,
                    "categories": "business",
                    "languages": "en",
                    "limit": 50
                },
                timeout=15
            )
            self._call_count += 1
            
            if response.status_code != 200:
                logger.warning(f"MediaStack returned {response.status_code}")
                return []
            
            data = response.json()
            
            if "error" in data:
                logger.warning(f"MediaStack error: {data['error']}")
                return []
            
            articles = data.get("data", [])
            return [self._convert(a) for a in articles[:20]]
            
        except Exception as e:
            logger.error(f"MediaStack error: {e}")
            return []
    
    def _convert(self, article: dict) -> dict[str, Any]:
        """Convert MediaStack format to standard format."""
        return {
            "title": article.get("title", ""),
            "description": article.get("description", "")[:500] if article.get("description") else "",
            "content": article.get("description", ""),
            "source": {"name": article.get("source", "MediaStack")},
            "url": article.get("url", ""),
            "publishedAt": article.get("published_at", ""),
            "urlToImage": article.get("image", "")
        }


class NewsAggregator:
    """
    Aggregates news from multiple sources with automatic failover.
    
    Priority order:
    1. NewsAPI (if not rate limited)
    2. Finnhub
    3. Alpha Vantage
    4. MediaStack
    5. RSS Feeds (always available)
    """
    
    def __init__(self):
        self.sources: list[NewsSource] = []
        self.seen_ids: set[str] = set()
        
        # Initialize all available sources
        settings = get_settings()
        
        if hasattr(settings, 'finnhub_api_key') and settings.finnhub_api_key:
            self.sources.append(FinnhubSource())
            logger.info("Finnhub source enabled")
            
        if hasattr(settings, 'alphavantage_api_key') and settings.alphavantage_api_key:
            self.sources.append(AlphaVantageSource())
            logger.info("Alpha Vantage source enabled")
            
        if hasattr(settings, 'mediastack_api_key') and settings.mediastack_api_key:
            self.sources.append(MediaStackSource())
            logger.info("MediaStack source enabled")
    
    def fetch_all(self, query: str = None) -> list[dict[str, Any]]:
        """
        Fetch from all available sources, deduplicate, and return.
        """
        all_articles = []
        
        for source in self.sources:
            try:
                articles = source.fetch(query)
                logger.info(f"{source.name}: fetched {len(articles)} articles")
                all_articles.extend(articles)
            except Exception as e:
                logger.warning(f"{source.name} failed: {e}")
                continue
        
        # Add RSS as final fallback
        try:
            from src.connectors.rss_connector import get_rss_connector
            rss = get_rss_connector()
            rss_articles = rss.fetch_articles(query)
            logger.info(f"RSS: fetched {len(rss_articles)} articles")
            
            # Convert RSS format
            for a in rss_articles:
                all_articles.append({
                    "title": a.get("title", ""),
                    "description": a.get("description", ""),
                    "content": a.get("content", ""),
                    "source": {"name": a.get("source", "RSS")},
                    "url": a.get("url", ""),
                    "publishedAt": a.get("published_at", ""),
                    "urlToImage": a.get("image_url", "")
                })
        except Exception as e:
            logger.warning(f"RSS fallback failed: {e}")
        
        # Deduplicate
        unique = []
        for article in all_articles:
            article_id = self._generate_id(article)
            if article_id not in self.seen_ids:
                self.seen_ids.add(article_id)
                unique.append(article)
        
        logger.info(f"News aggregator: {len(unique)} unique articles from {len(self.sources) + 1} sources")
        return unique
    
    def _generate_id(self, article: dict) -> str:
        """Generate unique ID for deduplication."""
        content = f"{article.get('title', '')}{article.get('url', '')}"
        return hashlib.md5(content.encode()).hexdigest()


# Singleton
_aggregator: NewsAggregator | None = None


def get_news_aggregator() -> NewsAggregator:
    """Get or create news aggregator singleton."""
    global _aggregator
    if _aggregator is None:
        _aggregator = NewsAggregator()
    return _aggregator
