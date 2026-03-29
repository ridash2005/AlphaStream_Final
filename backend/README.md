# AlphaStream India — Backend

FastAPI backend for AlphaStream India, an AI-powered Indian stock market analytics platform.

## Architecture Overview

| Layer | Technology |
|---|---|
| API server | FastAPI + Uvicorn |
| Agent orchestration | LangGraph (NLQ pipeline) |
| Analytics store | DuckDB (`market_analytics.duckdb`) |
| LLM | Google Vertex AI (Gemini 2.0 Flash default) |
| Market data | yfinance, NSE/BSE connectors, WorldMonitor |
| Streaming | Server-Sent Events (SSE) for NLQ, optional Pathway RAG |

---

## Agents (13)

| Agent | File | Responsibility |
|---|---|---|
| Sentiment | `sentiment_agent.py` | News sentiment scoring per ticker |
| Technical | `technical_agent.py` | RSI, MACD, Bollinger, Golden Cross signals |
| Risk | `risk_agent.py` | Portfolio risk scoring and VaR estimates |
| Decision | `decision_agent.py` | Fused buy/hold/sell recommendations |
| Insider | `insider_agent.py` | SAST/PIT insider-trade detection |
| Chart | `chart_agent.py` | Chart spec generation for frontend |
| Report | `report_agent.py` | PDF/text report generation |
| NLQ / QnA | `nlq/qna_agent.py` | LangGraph 7-node NLQ pipeline with SSE streaming |
| Flow | `flow_agent.py` | FII/DII institutional flow analysis |
| Pattern | `pattern_agent.py` | Candlestick pattern detection |
| Backtest | `backtest_agent.py` | Historical signal backtesting |
| Screener | (market router) | Multi-factor stock screener |
| Anomaly | `anomaly_agent.py` | Volume/price anomaly detection |

### NLQ Agent — LangGraph Pipeline

The NLQ agent runs a 7-node LangGraph graph for every natural-language question:

```
START → input_guardrail → enrich → router → analytics ┐
                                              text2sql  ├→ narrate → output_guardrail → END
                                              (direct)  ┘
```

- **input_guardrail** — topic filter, blocks off-topic queries
- **enrich** — cyclic web search (up to 3 rounds) + persistent user memory
- **router** — classifies query into one of 10 intents (SIGNAL_QUERY, INSIDER_QUERY, FLOW_QUERY, STOCK_LOOKUP, NEWS_QUERY, PORTFOLIO_AWARE, AD_HOC, GREETING, SIGNAL_DEF, OFF_TOPIC)
- **analytics** — MCP tool calls (market_data, signal, search servers)
- **text2sql** — generates and executes SQL against DuckDB (30 s timeout, 5 000-row cap)
- **narrate** — LLM narrative synthesis with source citations
- **output_guardrail** — safety/quality check on final answer

Streaming responses are delivered via SSE (`POST /api/nlq/stream`).

---

## Analytics Layer — DuckDB

`market_analytics.duckdb` is the local analytics store. The NLQ agent queries it read-only via generated SQL.

- **Timeout**: 30 seconds per query
- **Row cap**: 5 000 rows (truncation flag appended if exceeded)
- **Tables**: OHLCV, signals, insider trades, FII/DII flows, insights, screener results

---

## MCP Tool Servers (3)

The NLQ agent connects to three MCP stdio servers at runtime:

| Server | File | Tools provided |
|---|---|---|
| market_data | `nlq/mcp_servers/market_data_server.py` | OHLCV, fundamentals, ticker lookup |
| signal | `nlq/mcp_servers/signal_server.py` | Alpha scores, detected signals |
| search | `nlq/mcp_servers/search_server.py` | News search, web context |

`nlq/mcp_servers/portfolio_server.py` exists but is not currently wired into the agent.

---

## Connectors

| Connector | File | Notes |
|---|---|---|
| NewsAPI | `news_connector.py` | Primary news source |
| Groww | `groww_connector.py` | Optional — live Indian market data, portfolio import |
| FRED | `macro_connector.py` | Optional — macro signals (rates, CPI, GDP) |
| yfinance | (used in agents) | OHLCV fallback for all tickers |
| NSE | `nse_connector.py` | NSE equity data |
| BSE | `bse_connector.py` | BSE filings and corporate actions |
| FII/DII | `fii_dii_connector.py` | Institutional flow data |
| WorldMonitor | `global_market_connector.py` | Global indices, VIX, Fear & Greed, commodities |
| RSS | `rss_connector.py` | Additional news feeds |
| SEC EDGAR | `sec_connector.py` | SEC filings (for US-listed Indian ADRs) |

---

## Setup

### Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) package manager
- Google Cloud project with Vertex AI enabled (for LLM)

### Install and run

```bash
cd backend
uv sync
cp .env.example .env   # then edit with your values
uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8000

# or use the convenience script (also manages optional Pathway RAG):
./start.sh
```

The API is available at `http://localhost:8000`.
Interactive docs (Swagger UI): `http://localhost:8000/docs`

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes | Path to GCP service-account JSON |
| `GCP_PROJECT_ID` | Yes | Google Cloud project ID |
| `GCP_REGION` | Yes | Vertex AI region (default: `us-central1`) |
| `VERTEX_MODEL` | No | Gemini model (default: `gemini-2.0-flash`) |
| `NEWS_API_KEY` | Yes | Real-time news (newsapi.org) |
| `GROWW_API_TOKEN` | No | Groww portfolio import (JWT from app) |
| `FRED_API_KEY` | No | Macro signals (fred.stlouisfed.org) |
| `DUCKDB_PATH` | No | Path to DuckDB file (default: `market_analytics.duckdb`) |
| `ENABLE_PATHWAY` | No | Set `true` to activate Pathway streaming RAG |
| `ADAPTIVE_RAG_URL` | No | Pathway RAG server URL (default: `http://localhost:8001`) |
| `FINNHUB_API_KEY` | No | Fallback news source |
| `ALPHAVANTAGE_API_KEY` | No | Fallback news/data source |
| `LOG_LEVEL` | No | Logging verbosity: `debug`/`info`/`warning`/`error` |
| `REFRESH_INTERVAL` | No | News poll interval in seconds (default: `30`) |

---

## API Reference

Full endpoint list with request/response schemas: `http://localhost:8000/docs`

Key endpoints by router:

### Market (`/api/`)
| Method | Path | Description |
|---|---|---|
| GET | `/api/radar` | Top N opportunity signals by Alpha Score |
| GET | `/api/patterns/{ticker}` | Detected chart patterns |
| GET | `/api/backtest/{ticker}/{pattern}` | Historical signal backtest |
| GET | `/api/flows` | FII/DII institutional flow analysis |
| GET | `/api/screener` | Multi-factor stock screener |
| GET | `/api/anomalies/{ticker}` | Volume/price anomaly detection |
| GET | `/api/ohlcv/{ticker}` | OHLCV price history |
| GET | `/api/fundamentals/{ticker}` | Fundamental data |
| GET | `/api/bulk-deals` | NSE bulk/block deals |
| GET | `/api/news` | Latest market news |
| GET | `/api/tickers` | Full ticker universe |
| POST | `/api/portfolio` | Set portfolio holdings |
| GET | `/api/portfolio/summary` | Portfolio summary with live P&L |
| GET | `/api/filings/{ticker}` | Analyzed corporate filings |

### NLQ (`/api/`)
| Method | Path | Description |
|---|---|---|
| POST | `/api/nlq` | Blocking natural-language query |
| POST | `/api/nlq/stream` | SSE streaming natural-language query |

### Insights (`/api/`)
| Method | Path | Description |
|---|---|---|
| GET | `/api/insights` | List AI-generated alerts |
| GET | `/api/insights/count` | Unread alert count |
| POST | `/api/insights/mark-read` | Mark alert(s) as read |
| POST | `/api/insights/generate` | Trigger insight generation |

### Global Market (`/api/global/`)
| Method | Path | Description |
|---|---|---|
| GET | `/api/global/indices` | Global stock indices |
| GET | `/api/global/commodities` | Commodity futures |
| GET | `/api/global/crypto` | BTC/ETH quotes |
| GET | `/api/global/vix` | VIX volatility index |
| GET | `/api/global/fear-greed` | CNN Fear & Greed Index |
| GET | `/api/global/sectors` | US sector ETF performance |
| GET | `/api/global/macro` | Macro signals (FRED) |
| GET | `/api/global/currencies` | Currency pairs |
| GET | `/api/global/geo-risk` | Geopolitical risk signals |

---

## Testing

```bash
uv run pytest tests/ -v
```
