# AlphaStream India

**AI-Powered Investment Intelligence for the Indian Investor**

> *14 crore+ demat accounts. Most retail investors flying blind. AlphaStream India turns ET Markets data into actionable, money-making decisions.*

Built for **ET AI Hackathon 2026** — Problem Statement 6: AI for the Indian Investor.

---

## What It Does

AlphaStream India is a real-time investment intelligence platform that combines **multi-agent signal detection**, **NLQ (Natural Language Query)** analytics, and **backtested signals** to surface opportunities other investors miss.

### Three Core Features (PS6)

| Feature | Description |
|---|---|
| **Opportunity Radar** | AI monitors NSE/BSE filings, insider trades, FII/DII flows, chart patterns — surfaces signals with Alpha Score (0-100) |
| **Chart Pattern Intelligence** | Rule-based detection (RSI divergence, MACD crossover, Bollinger breakout, golden cross) with historical backtest success rates |
| **Market ChatGPT Next Gen** | NLQ agent with Text2SQL pipeline — grounded answers from real data, not LLM hallucination. Portfolio-aware, source-cited responses |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Indian Data Sources                                                 │
│  NSE API · BSE API · FII/DII (NSDL) · Groww API · ET Markets RSS   │
└──────────────┬──────────────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────────────┐
│  Pathway Streaming Engine (Real-time <2s)                            │
│  News ingestion → Chunking → Embedding → Adaptive RAG               │
└──────────────┬──────────────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────────────┐
│  Multi-Agent System (11 agents)                                      │
│  Sentiment · Technical · Risk · Decision · Pattern · Backtest        │
│  Filing · Flow · Insider · Chart · Report                            │
└──────────────┬──────────────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────────────┐
│  NLQ Agent (LangGraph)                                               │
│  Router → Text2SQL (schema link → plan → generate → guardrails       │
│  → correction loop) → Narrate (source-cited, chart specs)            │
│  MCP Servers: market_data · signals · portfolio                      │
└──────────────┬──────────────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────────────┐
│  Fusion Engine                                                       │
│  Alpha Score = weighted(filing + technical + insider/flow             │
│               + sentiment + backtest)                                 │
└──────────────┬──────────────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────────────┐
│  React Dashboard                                                     │
│  Opportunity Radar · NLQ Chat Panel · Market Heatmap · Agent Radar   │
│  Insider Activity · PDF Reports · WebSocket Real-time                │
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
- Python 3.11+
- Node.js 18+
- GCP service account (for Vertex AI)

### Setup

```bash
# Clone
git clone https://github.com/YOUR_REPO/AlphaStream-India.git
cd AlphaStream-India

# Backend
cd backend
cp .env.example .env  # Add your API keys
uv sync
.venv/bin/python -m src.data.market_schema  # Initialize DuckDB with Nifty 50 data

# Frontend
cd ../frontend
npm install

# Start
cd ..
bash start_demo.sh
```

### Environment Variables

```env
# Required
OPENROUTER_API_KEY=sk-or-...
NEWS_API_KEY=...
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
GCP_PROJECT_ID=your-project

# Optional (Indian market data)
GROWW_API_TOKEN=...
GROWW_TOTP_SECRET=...
```

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/nlq` | POST | Natural language query (blocking) |
| `/api/nlq/stream` | GET/POST | NLQ with SSE streaming |
| `/api/radar` | GET | Top signals by Alpha Score |
| `/api/patterns/{ticker}` | GET | Chart pattern detection |
| `/api/backtest/{ticker}/{pattern}` | GET | Historical backtest |
| `/api/flows` | GET | FII/DII flow analysis |
| `/api/portfolio` | POST | Set user portfolio |
| `/api/ohlcv/{ticker}` | GET | OHLCV for charting |
| `/api/insights` | GET | Ambient AI alerts |
| `/recommend` | POST | Trading recommendation |
| `/ws/stream/{ticker}` | WS | Real-time updates |

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

Built for ET AI Hackathon 2026 — Problem Statement 6

---

## License

MIT
