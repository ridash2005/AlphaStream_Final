"""
Multi-Source News Aggregator - "Herd of Knowledge" Engine.

Aggregates news from ALL available sources simultaneously for comprehensive
market intelligence. This is the PRIMARY news engine, not a fallback.

Sources:
- NewsAPI.org (breaking news)
- Finnhub (60 calls/min free)
- Alpha Vantage News (500 calls/day free)
- MediaStack (500 calls/month free)
- RSS Feeds (unlimited, free)

The "herd of knowledge" approach ensures:
1. No single point of failure
2. Broader news coverage
3. Multiple perspectives on the same events
4. Resilience to rate limits
"""

import logging
import time
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional
from abc import ABC, abstractmethod
import concurrent.futures

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


class NewsAPISource(NewsSource):
    """
    NewsAPI.org - Breaking news and articles.
    Free tier limited, but included in the herd for coverage.
    """
    
    name = "NewsAPI"
    BASE_URL = "https://newsapi.org/v2/everything"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or get_settings().newsapi_key
        self._rate_limited = False
    
    def fetch(self, query: str = None) -> list[dict[str, Any]]:
        if not self.api_key or self._rate_limited:
            return []
        
        try:
            # NewsAPI free tier requires searching older articles (not real-time)
            # Extend search to 7 days to get results on free tier
            from_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
            
            response = requests.get(
                self.BASE_URL,
                params={
                    "q": query or "stock market earnings trading",
                    "sortBy": "publishedAt",
                    "pageSize": 50,
                    "apiKey": self.api_key,
                    "from": from_date,
                    "language": "en",
                },
                timeout=15
            )
            
            if response.status_code == 429:
                logger.warning("NewsAPI rate limited - will skip in future calls")
                self._rate_limited = True
                return []
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            articles = data.get("articles", [])
            return [self._convert(a) for a in articles[:30]]
            
        except Exception as e:
            logger.debug(f"NewsAPI error: {e}")
            return []
    
    def _convert(self, article: dict) -> dict[str, Any]:
        """Convert NewsAPI format to standard format."""
        source = article.get("source", {})
        source_name = source.get("name", "NewsAPI") if isinstance(source, dict) else str(source)
        return {
            "title": article.get("title", ""),
            "description": article.get("description", "")[:500] if article.get("description") else "",
            "content": article.get("content", "") or article.get("description", ""),
            "source": {"name": source_name},
            "url": article.get("url", ""),
            "publishedAt": article.get("publishedAt", ""),
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
            # Finnhub requires a stock symbol - extract from query or use defaults
            # Common tickers to fetch news for if no specific ticker in query
            default_tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
            
            # Try to extract ticker from query
            if query:
                # Check if query looks like a ticker (all caps, 1-5 letters)
                query_upper = query.upper().strip()
                if query_upper.isalpha() and len(query_upper) <= 5:
                    symbols = [query_upper]
                else:
                    # Use defaults for general queries
                    symbols = default_tickers[:3]  # Fetch top 3 to reduce API calls
            else:
                symbols = default_tickers[:3]
            
            all_articles = []
            for symbol in symbols:
                # Get company news for this symbol
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
                
                if response.status_code == 200:
                    articles = response.json()
                    all_articles.extend([self._convert(a) for a in articles[:10]])
                else:
                    logger.debug(f"Finnhub {symbol} returned {response.status_code}")
                
                # Small delay between requests to respect rate limits
                time.sleep(0.5)
            
            return all_articles[:30]  # Return max 30 articles
            
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
            # Use NEWS_SENTIMENT endpoint - requires valid tickers
            default_tickers = "AAPL,MSFT,GOOGL"
            
            # Try to extract ticker from query
            if query:
                query_upper = query.upper().strip()
                if query_upper.isalpha() and len(query_upper) <= 5:
                    tickers = query_upper
                else:
                    tickers = default_tickers
            else:
                tickers = default_tickers
            
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
    "Herd of Knowledge" News Engine.
    
    Aggregates news from ALL available sources simultaneously.
    This is the PRIMARY news engine, not a fallback.
    
    All sources contribute to comprehensive market intelligence:
    - NewsAPI (breaking news)
    - Finnhub (company-specific news)
    - Alpha Vantage (sentiment-tagged news)
    - MediaStack (general business news)
    - RSS (free, always available)
    """
    
    def __init__(self):
        self.sources: list[NewsSource] = []
        self.seen_ids: set[str] = set()
        
        # Initialize ALL sources - "Herd of Knowledge" approach
        settings = get_settings()
        
        # NewsAPI is part of the herd (not special primary)
        if hasattr(settings, 'newsapi_key') and settings.newsapi_key:
            self.sources.append(NewsAPISource())
            logger.info("☁️ NewsAPI source enabled")
        
        if hasattr(settings, 'finnhub_api_key') and settings.finnhub_api_key:
            self.sources.append(FinnhubSource())
            logger.info("📊 Finnhub source enabled")
            
        if hasattr(settings, 'alphavantage_api_key') and settings.alphavantage_api_key:
            self.sources.append(AlphaVantageSource())
            logger.info("📈 Alpha Vantage source enabled")
            
        if hasattr(settings, 'mediastack_api_key') and settings.mediastack_api_key:
            self.sources.append(MediaStackSource())
            logger.info("MediaStack source enabled")
    
    def fetch_all(self, query: str = None) -> list[dict[str, Any]]:
        """
        Fetch from ALL available sources in PARALLEL, deduplicate, and return.
        
        This is the "herd of knowledge" - all sources contribute simultaneously.
        """
        all_articles = []
        source_stats = {}
        
        # Log how many sources are configured
        logger.info(f"📡 Fetching from {len(self.sources)} sources: {[s.name for s in self.sources]}")
        
        # Parallel fetch from all API sources
        def fetch_source(source):
            try:
                articles = source.fetch(query)
                logger.debug(f"{source.name} returned {len(articles)} articles")
                return source.name, articles
            except Exception as e:
                logger.warning(f"{source.name} failed: {e}")
                return source.name, []
        
        # Use ThreadPoolExecutor for parallel fetching
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_source, src): src for src in self.sources}
            
            for future in concurrent.futures.as_completed(futures):
                source_name, articles = future.result()
                source_stats[source_name] = len(articles)
                all_articles.extend(articles)
                logger.info(f"  → {source_name}: {len(articles)} articles")
        
        # Add RSS (always free, no rate limits)
        try:
            from src.connectors.rss_connector import get_rss_connector
            rss = get_rss_connector()
            rss_articles = rss.fetch_articles(query)
            source_stats["RSS"] = len(rss_articles)
            
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
            logger.warning(f"RSS fetch failed: {e}")
            source_stats["RSS"] = 0
        
        # Deduplicate by title/URL hash
        unique = []
        for article in all_articles:
            article_id = self._generate_id(article)
            if article_id not in self.seen_ids:
                self.seen_ids.add(article_id)
                unique.append(article)
        
        # Log aggregation stats
        active_sources = [f"{k}:{v}" for k, v in source_stats.items() if v > 0]
        logger.info(f"📰 Herd of Knowledge: {len(unique)} unique articles from {len(active_sources)} sources ({', '.join(active_sources)})")
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
