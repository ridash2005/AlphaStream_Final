"""
Simple polling mechanism for live news ingestion.
Runs in a background thread and pushes articles to a callback.
"""

import logging
import time
import threading
import hashlib
from datetime import datetime, timedelta
from typing import Callable, Any

import requests
from src.config import get_settings

logger = logging.getLogger(__name__)

class NewsPoller:
    """
    Polls NewsAPI and pushes articles to a callback function.
    """
    
    def __init__(self, callback: Callable[[dict[str, Any]], None], query: str = "stock market", interval: int = 60):
        self.callback = callback
        self.query = query
        self.interval = interval
        self.settings = get_settings()
        self.seen_ids = set()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self):
        """Start polling in a background thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("NewsPoller already running")
            return
            
        logger.info(f"Starting NewsPoller (interval={self.interval}s)")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
    def stop(self):
        """Stop polling."""
        if self._thread:
            logger.info("Stopping NewsPoller...")
            self._stop_event.set()
            self._thread.join(timeout=5)
            logger.info("NewsPoller stopped")

    def _run_loop(self):
        """Main polling loop."""
        while not self._stop_event.is_set():
            try:
                self._poll()
            except Exception as e:
                logger.error(f"NewsPoller error: {e}")
            
            # Wait for interval or stop signal
            if self._stop_event.wait(self.interval):
                break

    def _poll(self):
        """Fetch and process articles."""
        if not self.settings.newsapi_key:
            logger.warning("NewsAPI key missing, skipping poll")
            return

        # Fetch last 24h
        from_date = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        
        params = {
            "q": self.query,
            "sortBy": "publishedAt",
            "pageSize": 20, # Limit fetch size
            "apiKey": self.settings.newsapi_key,
            "from": from_date,
            "language": "en",
        }

        try:
            response = requests.get("https://newsapi.org/v2/everything", params=params, timeout=10)
            if response.status_code == 429:
                logger.warning("NewsAPI rate limit hit")
                return
            if response.status_code != 200:
                logger.warning(f"NewsAPI error {response.status_code}")
                return
                
            data = response.json()
            articles = data.get("articles", [])
            
            new_count = 0
            for article in articles:
                # Generate stable ID
                content_str = f"{article.get('title')}{article.get('url')}"
                article_id = hashlib.sha256(content_str.encode()).hexdigest()[:16]
                
                if article_id not in self.seen_ids:
                    self.seen_ids.add(article_id)
                    
                    # Prepare article dict matching ingestion schema
                    ingest_data = {
                        "id": article_id,
                        "title": article.get("title", ""),
                        "content": article.get("description", "") or article.get("content", "") or "",
                        "source": article.get("source", {}).get("name", "Unknown"),
                        "url": article.get("url", ""),
                        "published_at": article.get("publishedAt", ""),
                    }
                    
                    # Send to pipeline
                    self.callback(ingest_data)
                    new_count += 1
            
            if new_count > 0:
                logger.info(f"NewsPoller: Ingested {new_count} new articles")
                
        except Exception as e:
            logger.error(f"Polling request failed: {e}")
