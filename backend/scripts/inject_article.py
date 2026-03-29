"""
Inject a news article into AlphaStream for real-time testing.

Usage:
  uv run python scripts/inject_article.py "Title" "Content" --ticker RELIANCE --source "ET Markets"
"""

import argparse
import requests
from datetime import datetime, timezone

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich import box
import json

console = Console()


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

    console.print(Panel.fit(
        f"[bold cyan]Injecting article into AlphaStream[/bold cyan]\n"
        f"[dim]Ticker:[/dim] [bold]{ticker.upper() or '(none)'}[/bold]   "
        f"[dim]Source:[/dim] [bold]{source}[/bold]",
        border_style="cyan",
        padding=(0, 2),
    ))
    console.print()

    with console.status("[cyan]POSTing to /ingest ...[/cyan]"):
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            console.print("[bold green]✅ Article ingested successfully![/bold green]")
            console.print()

            # Show the response as syntax-highlighted JSON
            console.print(Syntax(
                json.dumps(data, indent=2, ensure_ascii=False),
                "json",
                theme="monokai",
                line_numbers=False,
                word_wrap=True,
            ))

        except requests.exceptions.ConnectionError:
            console.print("[bold red]✗ Connection refused — is the backend running?[/bold red]")
            console.print("[dim]  Start it with:  cd backend && bash start.sh[/dim]")
        except requests.exceptions.HTTPError as e:
            console.print(f"[bold red]✗ HTTP {e.response.status_code}:[/bold red] {e.response.text[:200]}")
        except Exception as e:
            console.print(f"[bold red]✗ Error:[/bold red] {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inject a news article into AlphaStream.")
    parser.add_argument("title", help="Article title")
    parser.add_argument("content", help="Article content")
    parser.add_argument("--ticker", "-t", default="", help="NSE ticker (e.g. RELIANCE, TCS)")
    parser.add_argument("--source", "-s", default="Manual Inject", help="Source name (e.g. 'ET Markets')")

    args = parser.parse_args()
    inject_article(args.title, args.content, ticker=args.ticker, source=args.source)
