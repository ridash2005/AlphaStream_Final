#!/usr/bin/env python3
import json
import argparse
import requests
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.text import Text
from rich import box

# Configuration
BACKEND_URL = "http://localhost:8000"
DATA_FILE = Path(__file__).parent / "demo_data.json"
INSIDER_DATA_FILE = Path(__file__).parent.parent / "backend/data/demo_insider.json"

console = Console()

def load_scenarios():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

NIFTY_50 = {
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "HDFC", "BHARTIARTL",
    "ITC", "KOTAKBANK", "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "BAJFINANCE", "HCLTECH",
    "SUNPHARMA", "TITAN", "ULTRACEMCO", "WIPRO", "NESTLEIND", "TECHM", "BAJAJFINSV",
    "POWERGRID", "NTPC", "ONGC", "JSWSTEEL", "TATAMOTORS", "TATASTEEL", "DIVISLAB",
    "ADANIPORTS", "DRREDDY", "CIPLA", "EICHERMOT", "HEROMOTOCO", "BPCL", "COALINDIA",
    "APOLLOHOSP", "SBILIFE", "HDFCLIFE", "M&M", "SBIN", "GRASIM", "INDUSINDBK",
    "BRITANNIA", "UPL", "HINDALCO", "SHREECEM", "TATACONSUM", "BAJAJ-AUTO",
}


def inject_news(ticker: str, articles: list, progress: Progress, task_id) -> tuple[int, int]:
    ok = fail = 0
    for i, article in enumerate(articles):
        payload = article.copy()
        payload["title"] = payload["title"].format(ticker=ticker)
        payload["content"] = payload["content"].format(ticker=ticker)
        if payload["published_at"] == "NOW":
            payload["published_at"] = datetime.utcnow().isoformat()
        payload.setdefault("tickers", [ticker.upper()])

        progress.update(task_id, description=f"[cyan]Injecting article {i+1}/{len(articles)}[/cyan]")
        try:
            resp = requests.post(f"{BACKEND_URL}/ingest", json=payload, timeout=30)
            if resp.status_code == 200:
                ok += 1
                console.print(f"  [green]✓[/green] {payload['title'][:70]}")
            else:
                fail += 1
                console.print(f"  [red]✗[/red] {payload['title'][:70]} ([yellow]{resp.status_code}[/yellow])")
        except Exception as e:
            fail += 1
            console.print(f"  [red]✗ Error:[/red] {e}")
        progress.advance(task_id)
    return ok, fail


def create_insider_override(ticker: str, transactions: list) -> None:
    INSIDER_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.now()
    processed = []
    for tx in transactions:
        t = tx.copy()
        t["ticker"] = ticker
        if t["filing_date"] == "TODAY":
            t["filing_date"] = today.strftime("%Y-%m-%d")
        elif t["filing_date"] == "YESTERDAY":
            t["filing_date"] = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        processed.append(t)
    with open(INSIDER_DATA_FILE, "w") as f:
        json.dump({ticker: processed}, f, indent=2)


def check_backend() -> bool:
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="Run AlphaStream Demo Scenario")
    parser.add_argument("--ticker", type=str, default="RELIANCE", help="NSE ticker symbol (default: RELIANCE)")
    parser.add_argument("--scenario", type=str, choices=["bullish", "bearish"], required=True)
    args = parser.parse_args()
    ticker = args.ticker.upper()
    scenario = args.scenario

    color = "green" if scenario == "bullish" else "red"
    icon  = "📈" if scenario == "bullish" else "📉"

    console.print(Panel.fit(
        f"[bold {color}]{icon}  AlphaStream India — {scenario.upper()} Demo[/bold {color}]\n"
        f"[dim]Ticker:[/dim] [bold white]{ticker}[/bold white]   "
        f"[dim]Backend:[/dim] [bold white]{BACKEND_URL}[/bold white]",
        border_style=color,
        padding=(1, 4),
    ))

    # Validate ticker
    if ticker not in NIFTY_50:
        console.print(f"[yellow]⚠  '{ticker}' is not in the Nifty 50 universe — continuing anyway.[/yellow]")

    # Check backend alive
    with console.status("[bold cyan]Checking backend health...[/bold cyan]"):
        alive = check_backend()
    if not alive:
        console.print(f"[bold red]✗ Backend not reachable at {BACKEND_URL}[/bold red]")
        console.print("[dim]  Start it with:  cd backend && bash start.sh[/dim]")
        raise SystemExit(1)
    console.print("[green]✓ Backend is healthy[/green]\n")

    scenarios = load_scenarios()
    scenario_data = scenarios.get(scenario)
    if not scenario_data:
        console.print(f"[red]Error: scenario '{scenario}' not found in demo_data.json[/red]")
        raise SystemExit(1)

    articles = scenario_data["news"]
    insider  = scenario_data["insider"]

    # ── Step 1: Insider override ──────────────────────────────────────────────
    console.rule("[bold]Step 1/2 — Insider Activity Override[/bold]")
    with console.status("[cyan]Writing insider transactions...[/cyan]"):
        create_insider_override(ticker, insider)
    # Print a summary table
    tbl = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold magenta")
    tbl.add_column("Name", style="white")
    tbl.add_column("Type", style="cyan")
    tbl.add_column("Qty", justify="right", style="yellow")
    tbl.add_column("Value", justify="right")
    for tx in insider:
        sign = "+" if tx.get("transaction_type", "BUY") == "BUY" else "-"
        val  = tx.get("transaction_value", 0)
        tbl.add_row(
            tx.get("insider_name", "—"),
            tx.get("transaction_type", "—"),
            f"{sign}{tx.get('quantity', 0):,}",
            f"₹{val/1e7:.1f}Cr" if val else "—",
        )
    console.print(tbl)
    console.print(f"[green]✓ {len(insider)} insider transaction(s) written[/green]\n")

    # ── Step 2: News injection ────────────────────────────────────────────────
    console.rule("[bold]Step 2/2 — News Article Injection[/bold]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TaskProgressColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task("[cyan]Starting...[/cyan]", total=len(articles))
        ok, fail = inject_news(ticker, articles, progress, task)

    status_color = "green" if fail == 0 else "yellow"
    console.print(f"\n[{status_color}]Injected {ok}/{len(articles)} articles ({fail} failed)[/{status_color}]\n")

    # ── Summary panel ─────────────────────────────────────────────────────────
    instructions = Text()
    instructions.append("1. ", style="bold yellow")
    instructions.append(f"Open frontend → ")
    instructions.append("http://localhost:5173\n", style="bold cyan underline")
    instructions.append("2. ", style="bold yellow")
    instructions.append(f"Search ticker: ")
    instructions.append(f"{ticker}\n", style="bold white")
    instructions.append("3. ", style="bold yellow")
    instructions.append("Overview tab → check Recommendation & Alpha Score\n")
    instructions.append("4. ", style="bold yellow")
    instructions.append("Signals tab → Opportunity Radar for new signals\n")
    instructions.append("5. ", style="bold yellow")
    instructions.append("Global Intelligence → FII/DII Flows chart\n")
    instructions.append("6. ", style="bold yellow")
    instructions.append("Ask NLQ: ")
    instructions.append(f"\"What is the latest news on {ticker}?\"\n", style="italic cyan")

    console.print(Panel(
        instructions,
        title=f"[bold {color}]✅ Demo Ready — {scenario.upper()}[/bold {color}]",
        border_style=color,
        padding=(1, 2),
    ))


if __name__ == "__main__":
    main()
