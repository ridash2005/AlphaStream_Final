"""
Script to inject a manual article to test real-time updates.
Usage: uv run python scripts/inject_article.py "Title" "Content" --ticker RELIANCE --source "ET Markets"
"""

import argparse
import requests
from datetime import datetime, timezone


def inject_article(title: str, content: str, ticker: str = "", source: str = "Manual Inject") -> None:
    url = "http://localhost:8000/ingest"

    payload = {
        "title": title,
        "content": content,
        "source": source,
        "url": f"http://test.alphastream.in/{datetime.now(timezone.utc).timestamp():.0f}",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "tickers": [ticker.upper()] if ticker else [],
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        print(f"✅ Success! Ingested article: {title}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"❌ Failed to ingest: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inject a news article into AlphaStream.")
    parser.add_argument("title", help="Article title")
    parser.add_argument("content", help="Article content")
    parser.add_argument("--ticker", "-t", default="", help="NSE ticker (e.g. RELIANCE, TCS)")
    parser.add_argument("--source", "-s", default="Manual Inject", help="Source name")

    args = parser.parse_args()
    inject_article(args.title, args.content, ticker=args.ticker, source=args.source)
