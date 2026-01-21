#!/usr/bin/env python3
import json
import argparse
import requests
import os
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
BACKEND_URL = "http://localhost:8000"
DATA_FILE = Path(__file__).parent / "demo_data.json"
INSIDER_DATA_FILE = Path(__file__).parent.parent / "backend/data/demo_insider.json"

def load_scenarios():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def inject_news(ticker, articles):
    print(f"Injecting {len(articles)} news articles for {ticker}...")
    
    for article in articles:
        # Prepare article payload
        payload = article.copy()
        
        # Replace placeholders
        payload["title"] = payload["title"].format(ticker=ticker)
        payload["content"] = payload["content"].format(ticker=ticker)
        
        # Set timestamp
        if payload["published_at"] == "NOW":
            payload["published_at"] = datetime.utcnow().isoformat()
        
        try:
            response = requests.post(f"{BACKEND_URL}/ingest", json=payload)
            if response.status_code == 200:
                print(f"  ✓ Injected: {payload['title']}")
            else:
                print(f"  ✗ Failed: {payload['title']} ({response.status_code})")
        except Exception as e:
            print(f"  ✗ Error: {e}")

def create_insider_override(ticker, transactions):
    print(f"Creating insider data override for {ticker}...")
    
    # Ensure directory exists
    INSIDER_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Process transactions
    processed_txs = []
    for tx in transactions:
        tx_data = tx.copy()
        tx_data["ticker"] = ticker
        
        # Handle dates
        today = datetime.now()
        if tx_data["filing_date"] == "TODAY":
            tx_data["filing_date"] = today.strftime("%Y-%m-%d")
        elif tx_data["filing_date"] == "YESTERDAY":
            tx_data["filing_date"] = (today - timedelta(days=1)).strftime("%Y-%m-%d")
            
        processed_txs.append(tx_data)
        
    # Write to override file
    with open(INSIDER_DATA_FILE, "w") as f:
        json.dump({ticker: processed_txs}, f, indent=2)
        
    print(f"  ✓ Wrote {len(processed_txs)} transactions to {INSIDER_DATA_FILE}")

def main():
    parser = argparse.ArgumentParser(description="Run AlphaStream Demo Scenario")
    parser.add_argument("--ticker", type=str, required=True, help="Ticker symbol (e.g., AAPL)")
    parser.add_argument("--scenario", type=str, choices=["bullish", "bearish"], required=True, help="Scenario to run")
    
    args = parser.parse_args()
    
    scenarios = load_scenarios()
    scenario_data = scenarios.get(args.scenario)
    
    if not scenario_data:
        print(f"Error: Scenario '{args.scenario}' not found.")
        return
    
    print(f"🚀 Starting {args.scenario.upper()} demo for {args.ticker}...")
    
    # 1. Update Insider Data (File Override)
    create_insider_override(args.ticker, scenario_data["insider"])
    
    # 2. Inject News (API)
    inject_news(args.ticker, scenario_data["news"])
    
    print("\n✅ Demo setup complete!")
    print(f"1. Go to AlphaStream frontend")
    print(f"2. Search for: {args.ticker}")
    print(f"3. Observe {args.scenario} recommendation and insider activity.")

if __name__ == "__main__":
    main()
