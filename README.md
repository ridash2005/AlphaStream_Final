# AlphaStream India

**AI-Powered Investment Intelligence for the Indian Investor**

> *14 crore+ demat accounts. Most retail investors flying blind. AlphaStream India turns ET Markets data into actionable, money-making decisions.*

Built for **ET AI Hackathon 2026** - Problem Statement 6: AI for the Indian Investor.

---

## What It Does

AlphaStream India is a real-time investment intelligence terminal that combines **multi-agent signal detection**, **technical analysis overlays**, **NLQ analytics**, and **global market intelligence** to surface opportunities other investors miss.

### Core Features

| Feature | Description |
|---|---|
| **Tabbed Bloomberg Terminal** | 5-tab layout: Overview · Signals · Global Intel · Company · Portfolio - each focused on a different investor workflow |
| **Opportunity Radar** | AI monitors NSE/BSE filings, insider trades, FII/DII flows, chart patterns - surfaces signals with Alpha Score (0-100) |
| **Technical Indicator Overlays** | RSI(14) sub-chart + SMA20/SMA50 line overlays on TradingView candlestick, togglable per ticker |
| **Fundamentals Panel** | PE, PB, ROE, Dividend Yield, Market Cap, 52-week H/L from Groww API - wired live |
| **Stock Screener** | Filter Nifty 50 universe by sector, signal direction, and alpha score using DuckDB `v_stock_screener` view |
| **Portfolio Manager** | Add/remove NSE holdings, track real-time P&L, ₹ totals, horizontal bar chart by ticker |
| **Watchlist** | Persistent (localStorage) watchlist of up to 20 NSE tickers with live sentiment scores |
| **Corporate Filings** | BSE announcements (dividends, results, board meetings) per ticker - 7/30/90-day view |
| **Anomaly Detection** | Online ML (River HalfSpaceTrees) flags price/volume anomalies fed from 3mo NSE OHLCV |
| **Global Market Intelligence** | Crypto (BTC/ETH/SOL/XRP) + Currencies (INR/USD, DXY) + US Sector ETFs - India-impact annotated |
| **Threat-aware News** | Articles sorted by threat level (critical/warning/info) with sentiment distribution donut chart |
| **Market ChatGPT Next Gen** | NLQ agent with Text2SQL pipeline - grounded answers from real data, portfolio-aware, source-cited |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Indian Data Sources                                                 │
│  NSE API · BSE API · FII/DII (NSDL) · Groww API · ET Markets RSS   │
│  FRED (macro) · WorldMonitor (global indices/commodities/crypto/FX)  │
└──────────────┬──────────────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────────────┐
│  Pathway Streaming Engine (Real-time <2s)                            │
│  News ingestion → Chunking → Embedding → Adaptive RAG               │
│  Threat classification (critical/warning/info) → DuckDB persist      │
└──────────────┬──────────────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────────────┐
│  Multi-Agent System (13 agents)                                      │
│  Sentiment · Technical · Risk · Decision · Pattern · Backtest        │
│  Filing · Flow · Insider · Chart · Report · Search · Anomaly         │
└──────────────┬──────────────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────────────┐
│  Analytics Layer (DuckDB)                                            │
│  fact_articles · fact_signals · fact_insider_trades · fact_filings   │
│  fact_fii_dii_flows · dim_stocks (Nifty 50)                         │
│  Views: v_stock_screener · v_signal_summary · v_sector_heatmap       │
└──────────────┬──────────────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────────────┐
│  NLQ Agent (LangGraph 7-node)                                        │
│  Guardrail → Enrich (web search) → Route → Text2SQL → Narrate        │
│  MCP Servers: market_data · signals · portfolio · search             │
└──────────────┬──────────────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────────────┐
│  React Terminal (5 tabs)                                             │
│  Overview: Candlestick+RSI/SMA · Recommendation · Fundamentals       │
│  Signals:  Screener · Opportunity Radar · Flow Chart                 │
│  Global:   Crypto/FX/Sectors · Fear&Greed · Macro · Commodities      │
│  Company:  Filings · News+Threat Badges · Watchlist                  │
│  Portfolio: Holdings · P&L Chart · Sector Allocation                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Streaming** | Pathway (real-time RAG, <2s latency) |
| **LLM** | Gemini 2.0 Flash (Vertex AI) + OpenRouter |
| **Agents** | LangChain + LangGraph (multi-agent orchestration) |
| **NLQ** | Text2SQL pipeline with guardrails + correction loop |
| **MCP** | FastMCP servers (market data, signals, portfolio) |
| **Database** | DuckDB (analytics), ChromaDB (vector search) |
| **Backend** | FastAPI + WebSocket + SSE streaming |
| **Frontend** | React 19, Zustand, Tailwind, Recharts, Framer Motion |
| **Market Data** | NSE API, BSE API, Groww API (TOTP), yfinance, ET Markets RSS |

---

## Quick Start

### Prerequisites

- **Python 3.11+** — backend runtime
- **Node.js 18+** — frontend build tooling
- **Google Cloud account** with Vertex AI enabled (for Gemini LLM)
- **API keys needed:** `NEWS_API_KEY` from [newsapi.org](https://newsapi.org/) (required), `GROWW_API_TOKEN` (optional)
- **Hardware:** 4 GB+ RAM recommended

### Step-by-Step Setup

**Step 1: Clone & configure**
```bash
git clone https://github.com/wildcraft958/AlphaStream_India.git
cd AlphaStream_India
```

**Step 2: Backend setup**
```bash
cd backend
uv sync
cp .env.example .env
# Edit .env — set GOOGLE_APPLICATION_CREDENTIALS, GCP_PROJECT_ID, and NEWS_API_KEY at minimum
```

**Step 3: Initialize database & start backend**
```bash
# Initialize DuckDB with Nifty 50 data
.venv/bin/python -m src.data.market_schema

# Start backend (cold start ~75s, then ready)
.venv/bin/python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```

**Step 4: Frontend setup**
```bash
cd ../frontend
npm install
```

**Step 5: Start frontend**
```bash
npm run dev
```

**Step 6: Open the dashboard**

Navigate to **http://localhost:5173**

### Minimal Mode (No API Keys)

If you don't have API keys yet, AlphaStream still runs using cached/mock data. Set in `backend/.env`:

```env
ENABLE_PATHWAY=false
NEWS_API_KEY=
GCP_PROJECT_ID=
```

The UI loads with cached article data and pre-computed recommendations — sufficient to evaluate the dashboard, agent outputs, and PDF report generation.

### Environment Variables

See `backend/.env.example` for the full reference. Key variables:

```env
# Required - GCP / Vertex AI (all LLM calls go through Gemini)
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
GCP_PROJECT_ID=your-project

# News APIs
NEWS_API_KEY=...

# Optional - Indian market data (enables fundamentals panel)
GROWW_API_TOKEN=...
GROWW_TOTP_SECRET=...

# Optional - enable Pathway streaming (adds 45s to startup)
ENABLE_PATHWAY=false
```

### Troubleshooting

**`ImportError: No module named 'pathway'`** — Set `ENABLE_PATHWAY=false` in `backend/.env`. The system runs without Pathway using a synchronous fallback.

**Port 8000 already in use** — Run `uvicorn src.api.app:app --port 8001` then set `VITE_API_URL=http://localhost:8001` in `frontend/.env`.

**Frontend loads blank** — Check `VITE_API_URL` in `frontend/.env` points to the running backend (default: `http://localhost:8000`).

**DuckDB error on startup** — Run `.venv/bin/python -m src.data.market_schema` from the `backend/` directory to initialise the database.

---

## API Endpoints

### Market Intelligence
| Endpoint | Method | Description |
|---|---|---|
| `/api/ohlcv/{ticker}` | GET | OHLCV + optional RSI/SMA20/SMA50 (`?indicators=true`) |
| `/api/fundamentals/{ticker}` | GET | PE, PB, ROE, Div Yield, 52w H/L (Groww API) |
| `/api/radar` | GET | Top signals by Alpha Score |
| `/api/screener` | GET | Filter stocks by sector/direction/alpha (DuckDB view) |
| `/api/patterns/{ticker}` | GET | Chart pattern detection |
| `/api/backtest/{ticker}/{pattern}` | GET | Historical backtest (5yr) |
| `/api/flows` | GET | FII/DII flow analysis |
| `/api/anomalies/{ticker}` | GET | Price/volume anomaly detection (River ML) |
| `/api/filings/{ticker}` | GET | BSE corporate announcements |
| `/api/portfolio` | POST | Set user portfolio holdings |
| `/api/portfolio/summary` | GET | Live P&L summary |

### Global Market (WorldMonitor)
| Endpoint | Method | Description |
|---|---|---|
| `/api/global/indices` | GET | NIFTY, SENSEX, S&P 500, DOW, etc. |
| `/api/global/commodities` | GET | Gold, Crude, Silver, Copper, etc. |
| `/api/global/crypto` | GET | BTC, ETH, SOL, XRP |
| `/api/global/currencies` | GET | INR/USD, DXY |
| `/api/global/sectors` | GET | 12 US sector ETF returns |
| `/api/global/fear-greed` | GET | CNN Fear & Greed index |
| `/api/global/macro` | GET | FRED macro signals + verdict |
| `/api/global/vix` | GET | VIX volatility index |
| `/api/global/geo-risk` | GET | India geopolitical risk score |

### NLQ & Core
| Endpoint | Method | Description |
|---|---|---|
| `/api/nlq` | POST | Natural language query (blocking) |
| `/api/nlq/stream` | GET/POST | NLQ with SSE streaming |
| `/api/insights` | GET | Ambient AI alerts |
| `/recommend` | POST | Full multi-agent recommendation |
| `/ws/stream/{ticker}` | WS | Real-time updates (rec, market, global) |

---

## Signal Types

| Signal | Detection Method | Backtest Available |
|---|---|---|
| RSI Divergence | Price vs RSI direction mismatch | Yes (5yr) |
| MACD Crossover | Signal line cross + histogram | Yes (5yr) |
| Bollinger Breakout | Squeeze → expansion | Yes (5yr) |
| Volume Breakout | >2x 20-day average | Yes (5yr) |
| Golden/Death Cross | 50 SMA vs 200 SMA | Yes (5yr) |
| Insider Buying | NSE SAST/PIT cluster detection | N/A |
| FII Streak | 5+ day consecutive net buying | N/A |
| Material Filing | LLM classification of BSE/NSE filings | N/A |

---

## Team

Built for ET AI Hackathon 2026 - Problem Statement 6

---

## License

MIT
