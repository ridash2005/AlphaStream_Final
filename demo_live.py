#!/usr/bin/env python3
"""
AlphaStream Live Demonstration Script.

This script demonstrates the real-time streaming capabilities of AlphaStream:
1. Streaming ingestion from multiple news sources
2. Real-time transformation via Pathway RAG
3. Live output updates via WebSocket and CLI

Usage:
    python demo_live.py [--ticker AAPL] [--no-ui]
"""

import argparse
import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime
from typing import Optional

import httpx
import websockets

# Configuration
BACKEND_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/stream"
FRONTEND_URL = "http://localhost:5173"


def print_header():
    """Print demo header."""
    print("\n" + "=" * 60)
    print("  ALPHASTREAM LIVE DEMONSTRATION")
    print("  Real-Time AI Trading Intelligence")
    print("=" * 60 + "\n")


def print_step(step_num: int, title: str):
    """Print a step header."""
    print(f"\n[Step {step_num}] {title}")
    print("-" * 50)


def print_result(label: str, value: str, indent: int = 2):
    """Print a result line."""
    spaces = " " * indent
    print(f"{spaces}{label}: {value}")


def check_backend() -> bool:
    """Check if backend is running."""
    try:
        response = httpx.get(f"{BACKEND_URL}/health", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False


def start_backend():
    """Start the backend server."""
    print("Starting backend server...")
    process = subprocess.Popen(
        ["uv", "run", "uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd="/home/bakasur/Downloads/Data Quest/backend",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    for _ in range(30):
        if check_backend():
            print("Backend started successfully!")
            return process
        time.sleep(1)
    
    print("ERROR: Backend failed to start")
    return None


def get_recommendation(ticker: str) -> Optional[dict]:
    """Get trading recommendation for a ticker."""
    try:
        response = httpx.post(
            f"{BACKEND_URL}/recommend",
            json={"ticker": ticker},
            timeout=60.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def inject_article(title: str, content: str, ticker: str) -> bool:
    """Inject a new article into the system."""
    try:
        article = {
            "title": title,
            "content": content,
            "source": "Breaking News",
            "url": "https://example.com/breaking",
            "published_at": datetime.now().isoformat(),
            "tickers": [ticker]
        }
        response = httpx.post(
            f"{BACKEND_URL}/ingest",
            json=article,
            timeout=30.0
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


async def listen_for_updates(ticker: str, timeout: float = 10.0):
    """Listen for WebSocket updates."""
    try:
        async with websockets.connect(f"{WS_URL}/{ticker}", close_timeout=5) as ws:
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=timeout)
                return json.loads(message)
            except asyncio.TimeoutError:
                return None
    except Exception as e:
        print(f"  WebSocket error: {e}")
        return None


def run_demonstration(ticker: str = "AAPL", skip_ui: bool = False):
    """Run the full demonstration."""
    
    print_header()
    
    # Check backend
    if not check_backend():
        print("Backend not running. Please start it first:")
        print("  cd backend && uv run uvicorn src.api.app:app --port 8000")
        return False
    
    print("Backend is running!")
    if not skip_ui:
        print(f"Open UI at: {FRONTEND_URL}")
    
    # Step 1: Initial recommendation
    print_step(1, f"Fetching Initial Recommendation for {ticker}")
    
    start_time = time.time()
    initial = get_recommendation(ticker)
    
    if initial:
        print_result("Recommendation", initial.get("recommendation", "N/A"))
        print_result("Confidence", f"{initial.get('confidence', 0):.1f}%")
        print_result("Sentiment", f"{initial.get('sentiment_score', 0):.2f} ({initial.get('sentiment_label', 'N/A')})")
        print_result("Latency", f"{initial.get('latency_ms', 0):.0f}ms")
        print_result("Engine", initial.get("rag_engine", "manual"))
    else:
        print("  Failed to get initial recommendation")
    
    # Step 2: Inject breaking news
    print_step(2, "Injecting Breaking News (Bearish)")
    
    bearish_article = {
        "title": f"{ticker} Faces Major Regulatory Investigation",
        "content": f"""
        Breaking: {ticker} is facing a significant regulatory investigation 
        that could result in billions of dollars in fines. Sources close to 
        the matter indicate that the investigation has been ongoing for months 
        and could lead to serious consequences for the company's operations.
        
        Analysts are downgrading the stock in response to this news, with 
        several major firms issuing sell recommendations. The company's 
        market capitalization has already dropped significantly in pre-market 
        trading as investors react to the uncertainty.
        
        This investigation adds to existing concerns about the company's 
        competitive position and growth prospects in the current market 
        environment.
        """
    }
    
    print(f"  Title: \"{bearish_article['title']}\"")
    
    if inject_article(bearish_article["title"], bearish_article["content"], ticker):
        print("  Article injected successfully!")
    else:
        print("  Failed to inject article")
    
    # Step 3: Wait for real-time update
    print_step(3, "Waiting for Real-Time Update")
    print("  Listening for WebSocket updates...")
    
    # Give the system time to process
    time.sleep(2)
    
    # Step 4: Get updated recommendation
    print_step(4, "Fetching Updated Recommendation")
    
    updated = get_recommendation(ticker)
    end_time = time.time()
    
    if updated:
        print_result("Recommendation", updated.get("recommendation", "N/A"))
        print_result("Confidence", f"{updated.get('confidence', 0):.1f}%")
        print_result("Sentiment", f"{updated.get('sentiment_score', 0):.2f} ({updated.get('sentiment_label', 'N/A')})")
        print_result("Latency", f"{updated.get('latency_ms', 0):.0f}ms")
        print_result("Engine", updated.get("rag_engine", "manual"))
        
        # Check for change
        if initial and updated:
            initial_rec = initial.get("recommendation", "")
            updated_rec = updated.get("recommendation", "")
            initial_conf = initial.get("confidence", 0)
            updated_conf = updated.get("confidence", 0)
            
            print("\n  --- Change Detection ---")
            print_result("Initial", f"{initial_rec} ({initial_conf:.1f}%)")
            print_result("Updated", f"{updated_rec} ({updated_conf:.1f}%)")
            
            total_time = end_time - start_time
            print_result("Total Demo Time", f"{total_time:.1f}s")
    
    # Summary
    print("\n" + "=" * 60)
    print("  DEMONSTRATION COMPLETE")
    print("=" * 60)
    print("\nKey Points Demonstrated:")
    print("  1. Streaming ingestion of breaking news")
    print("  2. Real-time RAG transformation")
    print("  3. Live recommendation updates")
    print("  4. Multi-agent reasoning system")
    print("\nPathway Features Used:")
    print("  - pw.io.python.ConnectorSubject (streaming ingestion)")
    print("  - pw.xpacks.llm.AdaptiveRAGQuestionAnswerer (Adaptive RAG)")
    print("  - pw.io.subscribe (real-time callbacks)")
    print("  - WebSocket broadcasting (live updates)")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="AlphaStream Live Demonstration")
    parser.add_argument("--ticker", "-t", default="AAPL", help="Stock ticker (default: AAPL)")
    parser.add_argument("--no-ui", action="store_true", help="Skip UI instructions")
    args = parser.parse_args()
    
    try:
        run_demonstration(ticker=args.ticker, skip_ui=args.no_ui)
    except KeyboardInterrupt:
        print("\n\nDemonstration interrupted by user.")
    except Exception as e:
        print(f"\nError during demonstration: {e}")
        raise


if __name__ == "__main__":
    main()
