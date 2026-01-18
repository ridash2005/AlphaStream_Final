"""
Script to inject a manual article to test real-time updates.
Usage: uv run python scripts/inject_article.py "Title" "Content" "Ticker"
"""

import sys
import argparse
import requests
import time

def inject_article(title, content, source="Manual Inject"):
    url = "http://localhost:8000/ingest"
    
    payload = {
        "title": title,
        "content": content,
        "source": source,
        "url": f"http://test.com/{time.time()}",
        "published_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"✅ Success! Ingested article: {title}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"❌ Failed to ingest: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inject a news article.")
    parser.add_argument("title", help="Article title")
    parser.add_argument("content", help="Article content")
    parser.add_argument("--source", default="Manual Inject", help="Source name")
    
    args = parser.parse_args()
    
    inject_article(args.title, args.content, args.source)
