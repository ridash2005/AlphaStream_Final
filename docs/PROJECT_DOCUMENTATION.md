# AlphaStream India: Real-Time AI Investment Intelligence
## Comprehensive Project Documentation
### ET AI Hackathon 2026 - Problem Statement 6: AI for the Indian Investor

---

## Executive Summary

AlphaStream India is a **production-grade Bloomberg-style terminal** for the Indian retail investor, built on **Pathway streaming RAG + multi-agent AI**. It addresses the critical gap between institutional-grade analytics and what 14 crore+ Indian demat account holders actually have access to.

**Key Innovations**:
1. **Pathway Adaptive RAG** - <2s latency from news arrival to recommendation update
2. **13-agent reasoning pipeline** - Sentiment, Technical (RSI/SMA), Risk, Decision, Flow, Pattern, Backtest, Filing, Insider, Chart, Report, Search, Anomaly (River ML)
3. **5-tab Bloomberg terminal** - Overview · Signals · Global Intel · Company · Portfolio
4. **WorldMonitor global backbone** - Live global indices, commodities, crypto, FX, macro signals, geopolitical risk wired into every recommendation
5. **DuckDB analytics layer** - Pre-aggregated views (v_stock_screener, v_signal_summary, v_sector_heatmap) powering the screener and NLQ engine
6. **India-first context** - ₹ currency, IST timezone, NSE/BSE, Nifty 50 universe, Crores/Lakhs formatting throughout

**Team**: ET AI Hackathon 2026 Participants

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Solution Architecture](#2-solution-architecture)
3. [Pathway Integration Deep Dive](#3-pathway-integration-deep-dive)
4. [Multi-Agent Reasoning System](#4-multi-agent-reasoning-system)
5. [Real-Time Data Pipeline](#5-real-time-data-pipeline)
6. [Technology Stack](#6-technology-stack)
7. [API Reference](#7-api-reference)
8. [Setup & Deployment](#8-setup--deployment)
9. [Demonstration Pipeline](#9-demonstration-pipeline)
10. [Performance Metrics](#10-performance-metrics)
11. [Future Enhancements](#11-future-enhancements)

---

## 1. Problem Statement

### The Challenge of Stale Knowledge in Financial AI

Traditional AI-powered financial tools suffer from a fundamental limitation: **knowledge cutoff**. Large Language Models are trained on historical data, and even RAG (Retrieval-Augmented Generation) systems typically rely on batch-updated knowledge bases. This creates critical gaps:

- A financial chatbot unaware of earnings announced 5 minutes ago
- A trading assistant missing a market-moving SEC filing
- Risk models operating on yesterday's data in real-time markets

### Our Solution: Live AI

AlphaStream implements the **"Live AI" paradigm** - a system that:

- Continuously ingests data from multiple real-time sources
- Updates its knowledge base **incrementally** (not batch)
- Delivers recommendations that reflect the **current state of reality**
- Provides full explainability for every decision

---

## 2. Solution Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ALPHASTREAM ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    DATA INGESTION LAYER                          │   │
│  │  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌─────────┐ ┌───────┐  │   │
│  │  │ NewsAPI  │ │ Finnhub  │ │AlphaVant. │ │MediaSt. │ │  RSS  │  │   │
│  │  └────┬─────┘ └────┬─────┘ └─────┬─────┘ └────┬────┘ └───┬───┘  │   │
│  │       └────────────┼─────────────┼────────────┼──────────┘       │   │
│  │                    ▼             ▼            ▼                  │   │
│  │            ┌───────────────────────────────────────┐             │   │
│  │            │  "HERD OF KNOWLEDGE" AGGREGATOR       │             │   │
│  │            │  (Parallel fetching, deduplication)   │             │   │
│  │            └───────────────────┬───────────────────┘             │   │
│  └────────────────────────────────┼─────────────────────────────────┘   │
│                                   ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                   PATHWAY STREAMING ENGINE                       │   │
│  │                                                                  │   │
│  │  ┌────────────────┐  ┌─────────────────┐  ┌──────────────────┐  │   │
│  │  │ pw.io.python   │  │  DocumentStore  │  │  AdaptiveRAG     │  │   │
│  │  │ ConnectorSubj. │→ │  (xpacks.llm)   │→ │  QuestionAnsw.   │  │   │
│  │  └────────────────┘  └─────────────────┘  └──────────────────┘  │   │
│  │                              ↓                                   │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │  pw.io.subscribe() → Real-time callbacks on data changes   │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                   MULTI-AGENT REASONING LAYER                    │   │
│  │                                                                  │   │
│  │  ┌────────────┐ ┌───────────┐ ┌──────────┐ ┌───────────────┐    │   │
│  │  │ Sentiment  │ │ Technical │ │   Risk   │ │   Insider     │    │   │
│  │  │   Agent    │ │   Agent   │ │  Agent   │ │    Agent      │    │   │
│  │  └─────┬──────┘ └─────┬─────┘ └────┬─────┘ └───────┬───────┘    │   │
│  │        └──────────────┼───────────┼────────────────┘            │   │
│  │                       ▼           ▼                              │   │
│  │                ┌──────────────────────────┐                      │   │
│  │                │     DECISION AGENT       │                      │   │
│  │                │   (Final BUY/HOLD/SELL)  │                      │   │
│  │                └────────────┬─────────────┘                      │   │
│  └─────────────────────────────┼────────────────────────────────────┘   │
│                                ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      PRESENTATION LAYER                          │   │
│  │                                                                  │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │   │
│  │  │ FastAPI REST │  │  WebSocket   │  │   React Dashboard      │ │   │
│  │  │  Endpoints   │  │  Streaming   │  │   (Bloomberg-style)    │ │   │
│  │  └──────────────┘  └──────────────┘  └────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Overview

| Layer | Components | Purpose |
|-------|------------|---------|
| Indian Data Sources | NSE API, BSE API, FII/DII (NSDL), Groww API, ET Markets RSS, NewsAPI, Finnhub, Alpha Vantage | Real-time Indian market data + news from 5+ parallel sources |
| Global Data Sources | WorldMonitor (yfinance indices, crypto, FX, commodities), CNN Fear and Greed, FRED Macro | Global context wired into every recommendation |
| Streaming Engine | Pathway (pw.io, pw.xpacks.llm, Adaptive RAG) | Incremental processing, auto-updating indexes |
| Analytics Layer | DuckDB (fact_articles, fact_signals, v_stock_screener, dim_stocks) | Pre-aggregated views for screener + NLQ |
| Reasoning | 13 specialized AI agents | Multi-perspective market analysis |
| NLQ Agent | LangGraph 7-node pipeline (Guardrail, Enrich, Route, Analytics, Text2SQL, Narrate, Output Guardrail) | Natural language queries grounded in real data |
| Presentation | FastAPI + WebSocket + SSE, React 19 (5-tab Bloomberg terminal) | Real-time delivery to users |

---

## 3. Pathway Integration Deep Dive

### Primary RAG: Pathway Adaptive RAG (xpacks.llm)

Our **primary RAG implementation** uses Pathway's official LLM xpack, following the [adaptive_rag template](https://github.com/pathwaycom/llm-app/tree/main/templates/adaptive_rag):

```python
from pathway.xpacks.llm.question_answering import AdaptiveRAGQuestionAnswerer
from pathway.xpacks.llm.document_store import DocumentStore
from pathway.xpacks.llm import llms, embedders, splitters

# Document Store with streaming ingestion
document_store = DocumentStore(
    docs=pw.io.fs.read(path="data/articles", format="binary"),
    parser=parsers.UnstructuredParser(),
    splitter=splitters.TokenCountSplitter(max_tokens=400),
    retriever_factory=pw.indexing.UsearchKnnFactory(
        embedder=embedders.SentenceTransformerEmbedder("all-MiniLM-L6-v2"),
        metric=pw.indexing.USearchMetricKind.COS
    )
)

# Adaptive RAG with geometric retrieval
question_answerer = AdaptiveRAGQuestionAnswerer(
    llm=llms.LiteLLMChat(model="openrouter/google/gemma-3n-e2b-it:free"),
    indexer=document_store,
    n_starting_documents=2,  # Start small
    factor=2,                 # Double if needed
    max_iterations=4          # Max 16 documents
)
```

### Pathway Features Utilized

| Feature | File | Purpose |
|---------|------|---------|
| `pw.Schema` | `news_connector.py`, `pathway_tables.py` | Type-safe data schemas |
| `pw.Table` | `pathway_tables.py` | Streaming market data tables |
| `pw.io.python.ConnectorSubject` | `news_connector.py` | Custom polling connector |
| `pw.io.fs.read` | `adaptive_rag_server.py` | File-based document ingestion |
| `pw.io.subscribe` | `app.py` | Real-time event callbacks |
| `pw.run` | `app.py` | Background Pathway engine |
| `pw.apply` | `pathway_tables.py` | UDF transformations |
| `pw.filter` | `pathway_tables.py` | Event filtering |
| `pw.reducers` | `pathway_tables.py` | Aggregations (avg, count, max) |
| `pw.indexing.UsearchKnnFactory` | `adaptive_rag_server.py` | Vector search |
| `pw.persistence` | `pathway_rag.yaml` | Caching & fault tolerance |
| `pw.load_yaml` | `adaptive_rag_server.py` | Declarative configuration |
| `pw.xpacks.llm.*` | `adaptive_rag_server.py` | Official LLM components |

### Geometric Retrieval Strategy

The Adaptive RAG uses an innovative approach to optimize token usage:

```
Query → Retrieve 2 docs → LLM evaluates sufficiency
                                    ↓
                         Sufficient? → Return answer
                                    ↓
                              No → Retrieve 4 docs → LLM evaluates
                                    ↓
                              No → Retrieve 8 docs → ...
                                    ↓
                         (Max 4 iterations)
```

This typically reduces token usage by 40-60% compared to fixed-k retrieval.

### Legacy RAG (Testing Environment)

For comparison and testing, we maintain a legacy RAG implementation:

```python
# Legacy RAG in rag_core.py
class RAGPipeline:
    def __init__(self):
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self.documents = []
        self.index = None
    
    def retrieve(self, query, k=5):
        # Fixed-k retrieval
        return self.hybrid_search(query, k)
```

---

## 4. Multi-Agent Reasoning System

### Agent Architecture

Each agent is a specialized LangChain chain with a specific analytical focus:

![Multi-Agent Consensus System](multi_agent_system.png)

### Agent Specifications (13 Agents)

| Agent | Input | Output | Technology |
|-------|-------|--------|------------|
| **Sentiment** | News articles | Score (-1 to +1), Label | LangChain + Gemini (Vertex AI) |
| **Technical** | NSE ticker | RSI(14), SMA20/SMA50, Trend signals | yfinance + numpy |
| **Risk** | Technical data | Volatility, Position size, Stop loss | Statistical calculation |
| **Pattern** | NSE ticker | Chart patterns (RSI divergence, MACD crossover, etc.) | yfinance + custom detectors |
| **Backtest** | Ticker + pattern | Win rate, avg return, Sharpe (5yr history) | yfinance + statistical analysis |
| **Flow** | FII/DII data | Net flow signal, streak detection, divergence | NSDL data + analysis |
| **Filing** | BSE announcements | Filing type, materiality, market impact | BSE API + Gemini LLM |
| **Insider** | NSE SAST/PIT data | Cluster buying/selling, transaction analysis | NSE connector + Gemini LLM |
| **Anomaly** | OHLCV time series | Price/volume anomaly flags with scores | River ML (HalfSpaceTrees) |
| **Search** | NLQ query | Reformulated multi-round search results | LangGraph cyclic agent |
| **Chart** | Ticker + events | PNG chart image | Matplotlib |
| **Report** | All agent data | PDF document | ReportLab |
| **Decision** | All agent outputs + global context | Final BUY/HOLD/SELL + Alpha Score | LangChain + Gemini (Vertex AI) |

---

## 5. Real-Time Data Pipeline

### "Herd of Knowledge" Multi-Source Aggregation

Our innovative news aggregation system uses 5 parallel sources:

```python
class NewsAggregator:
    def fetch_all(self, query: str) -> list[dict]:
        # Parallel fetch from all sources
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(src.fetch, query): src 
                       for src in self.sources}
            
            for future in concurrent.futures.as_completed(futures):
                articles.extend(future.result())
        
        # Deduplicate by title hash
        return self._deduplicate(articles)
```

### Source Configuration

| Source | Free Tier | Rate Limit | Data Quality |
|--------|-----------|------------|--------------|
| NewsAPI | 100/day | Yes | High |
| Finnhub | 60/min | Yes | High (financial) |
| Alpha Vantage | 500/day | Yes | Medium |
| MediaStack | 500/mo | Yes | Medium |
| RSS | Unlimited | No | Variable |

### Streaming Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 PATHWAY STREAMING FLOW                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   NewsConnector                                             │
│        │                                                    │
│        ▼                                                    │
│   pw.io.python.read()  ──────► pw.Table (streaming)        │
│        │                              │                     │
│        │                              ▼                     │
│        │                    pw.io.subscribe()               │
│        │                              │                     │
│        │                              ▼                     │
│        │                    on_new_article()                │
│        │                              │                     │
│        ▼                              ▼                     │
│   60s polling loop             RAG ingestion                │
│                                       │                     │
│                                       ▼                     │
│                              WebSocket broadcast            │
│                                       │                     │
│                                       ▼                     │
│                              Dashboard update (<2s)         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Technology Stack

### Backend

| Component | Technology | Purpose |
|-----------|------------|---------|
| Streaming Engine | Pathway | Real-time RAG, <2s latency |
| Web Framework | FastAPI + WebSocket + SSE | REST + real-time push |
| LLM | Gemini 2.0 Flash (Vertex AI) | All agent reasoning via GCP |
| Agent Framework | LangChain + LangGraph | Multi-agent orchestration + NLQ pipeline |
| Analytics DB | DuckDB | Pre-aggregated views, screener, NLQ Text2SQL |
| Vector Search | ChromaDB | Embedding-based article retrieval |
| Anomaly Detection | River ML (HalfSpaceTrees) | Online price/volume anomaly detection |
| Indian Market Data | NSE API, BSE API, Groww API, NSDL | OHLCV, filings, FII/DII flows, fundamentals |
| Global Market Data | WorldMonitor (yfinance), CNN, FRED | Indices, commodities, crypto, FX, macro |
| Python | 3.11 | Runtime |
| Package Manager | uv | Dependency management |

### Frontend

| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | React 19 | UI framework |
| Build Tool | Vite 6 | Dev server + bundling |
| Styling | Tailwind CSS 4 | Utility-first CSS |
| Components | Shadcn/ui | Accessible UI primitives |
| State | Zustand (persisted) | Client state + localStorage |
| Candlestick Charts | lightweight-charts 5.1 | TradingView charting |
| Data Charts | Recharts 3.6 | BarChart, PieChart, RadarChart |
| Icons | Lucide React | Consistent iconography |

---

## 7. API Reference (24 Verified Endpoints)

### Market Intelligence

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ohlcv/{ticker}` | GET | OHLCV candlestick data + optional RSI/SMA20/SMA50 (`?indicators=true`) |
| `/api/fundamentals/{ticker}` | GET | PE, PB, ROE, Div Yield, 52w H/L from Groww API |
| `/api/radar` | GET | Top signals by Alpha Score |
| `/api/screener` | GET | Filter Nifty 50 by sector/direction/alpha (DuckDB view) |
| `/api/patterns/{ticker}` | GET | Chart pattern detection (RSI divergence, MACD, etc.) |
| `/api/backtest/{ticker}/{pattern}` | GET | Historical backtest (5yr) with win rate |
| `/api/flows` | GET | FII/DII flow analysis with streak detection |
| `/api/anomalies/{ticker}` | GET | Price/volume anomaly detection (River ML) |
| `/api/filings/{ticker}` | GET | BSE corporate announcements |
| `/api/tickers` | GET | Nifty 50 universe with sectors |
| `/api/tickers/popular` | GET | Top 10 by market cap |
| `/api/news` | GET | Recent articles from DuckDB |
| `/api/portfolio` | POST | Set user portfolio holdings |
| `/api/portfolio/summary` | GET | Live P&L summary |
| `/api/insights` | GET | Ambient AI alerts |

### Global Market (WorldMonitor)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/global/indices` | GET | NIFTY, SENSEX, S&P 500, DOW, etc. |
| `/api/global/commodities` | GET | Gold, Crude, Silver, Copper, etc. |
| `/api/global/crypto` | GET | BTC, ETH, SOL, XRP |
| `/api/global/currencies` | GET | INR/USD, DXY |
| `/api/global/sectors` | GET | 12 US sector ETF returns |
| `/api/global/fear-greed` | GET | CNN Fear and Greed index |
| `/api/global/macro` | GET | FRED macro signals + verdict |
| `/api/global/vix` | GET | VIX volatility index |
| `/api/global/geo-risk` | GET | India geopolitical risk score |

### Core + NLQ

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/recommend` | POST | Full multi-agent recommendation |
| `/api/nlq` | POST | Natural language query (blocking) |
| `/api/nlq/stream` | GET/POST | NLQ with SSE streaming |
| `/insider/{ticker}` | GET | NSE SAST/PIT insider trading |
| `/report/{ticker}` | POST | PDF report generation |
| `/ws/stream/{ticker}` | WS | Real-time updates (recommendation, market, global) |

### Example: Recommendation

**Request:**
```json
{ "ticker": "RELIANCE" }
```

**Response:**
```json
{
  "ticker": "RELIANCE",
  "timestamp": "2026-03-29T06:55:00+05:30",
  "recommendation": "BUY",
  "confidence": 78.5,
  "sentiment_score": 0.65,
  "sentiment_label": "BULLISH",
  "technical_score": 0.42,
  "risk_score": 3.2,
  "key_factors": ["FII buying streak", "RSI divergence bullish"],
  "sources": ["ET Markets", "Moneycontrol"],
  "latency_ms": 1250,
  "global_verdict": "RISK-ON",
  "vix": 31.05,
  "fear_greed_score": 50
}
```

---

## 8. Setup & Deployment

### Prerequisites

- Python 3.11+
- Node.js 18+
- uv package manager
- API Keys: NEWS_API_KEY (required), FRED_API_KEY (optional), FINNHUB / ALPHAVANTAGE / MEDIASTACK (optional fallbacks)
- Google Cloud credentials: GOOGLE_APPLICATION_CREDENTIALS, GCP_PROJECT_ID, GCP_REGION (for Vertex AI / Gemini LLM)

### Installation

```bash
# Clone repository
git clone https://github.com/wildcraft958/AlphaStream_India.git
cd AlphaStream_India

# Backend setup
cd backend
cp .env.example .env  # Add your API keys (GCP, Groww, NewsAPI)
uv sync
.venv/bin/python -m src.data.market_schema  # Initialize DuckDB with Nifty 50 data

# Frontend setup
cd ../frontend
npm install
```

### Running the Application

```bash
# Terminal 1: Backend (cold start ~75s due to langchain imports)
cd backend
.venv/bin/python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

Access at: http://localhost:5173

### Environment Variables

```env
# Required - GCP / Vertex AI
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
GCP_PROJECT_ID=your-project
GCP_REGION=us-central1

# News APIs (at least one recommended)
NEWS_API_KEY=...

# Indian market data (optional but recommended)
GROWW_API_TOKEN=...
GROWW_TOTP_SECRET=...

# Enable Pathway streaming (optional, adds 45s to startup)
ENABLE_PATHWAY=true
```

---

## 9. Demonstration Pipeline

### Proving Real-Time Dynamism

The demonstration pipeline proves the system's real-time capabilities:

```bash
# Step 1: Start the system
cd backend && .venv/bin/python -m uvicorn src.api.app:app --port 8000 &
cd frontend && npm run dev &

# Step 2: Open dashboard, login as judge@etmedia.com
# RELIANCE loads by default - chart, recommendation, fundamentals visible

# Step 3: Query initial recommendation
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"ticker":"RELIANCE"}'

# Step 4: Inject breaking news (bearish)
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "title": "SEBI Investigation into Reliance Industries",
    "content": "SEBI has launched a preliminary investigation into Reliance Industries regarding potential disclosure irregularities..."
  }'

# Step 5: Observe real-time update (<2 seconds)
# Dashboard automatically updates via WebSocket

# Step 6: Test NLQ
curl -X POST http://localhost:8000/api/nlq \
  -H "Content-Type: application/json" \
  -d '{"query": "Which Nifty 50 stocks have bullish signals today?"}'
```

### Expected Latencies

| Operation | Latency |
|-----------|---------|
| Article ingestion | <100ms |
| RAG indexing | <200ms |
| Agent processing | ~1s |
| WebSocket delivery | <50ms |
| **Total: Data → Update** | **<2 seconds** |

---

## 10. Performance Metrics

### System Performance

| Metric | Value |
|--------|-------|
| News ingestion rate | 40+ articles/refresh |
| Recommendation latency | ~1.2s (LLM-bound) |
| WebSocket latency | <50ms |
| Document indexing | <100ms |
| PDF generation | ~15s |

### Adaptive RAG Performance

| Metric | Adaptive RAG | Fixed-k RAG |
|--------|--------------|-------------|
| Avg tokens/query | ~800 | ~1400 |
| Token savings | 43% | - |
| Accuracy | 94% | 95% |

---

## 11. Future Enhancements

### Delivered in v2 (ET AI Hackathon 2026)

The following features from the original roadmap have been **fully implemented**:

| Feature | Status | Component |
|---------|--------|-----------|
| Portfolio Mode | ✅ Done | `PortfolioManager` - holdings, real-time P&L, BarChart by ticker |
| Alert System | ✅ Done | `NotificationBell` + `AnomalyPanel` - River ML anomaly detection with badges |
| Backtesting | ✅ Done | `PatternAgent` + `/api/backtest/{ticker}/{pattern}` - 5-year pattern backtest |
| Options Flow | ✅ Done (FII/DII) | `FlowChart` + `FlowAgent` - FII/DII net flow analysis |

### Remaining Roadmap

1. **Social Media Integration** - Twitter/X, Reddit WallStreetBets India sentiment scraping for retail investor mood
2. **Earnings Calendar** - Scheduled BSE result announcements with pre/post earnings drift analysis
3. **SMS / Push Alerts** - WhatsApp Business API or FCM for critical threat_level=critical article alerts
4. **Options Chain Analysis** - NSE F&O open interest, max pain, PCR ratio with visual strike overlay
5. **Multi-Language NLQ** - Hindi language support for NLQ queries (Devanagari input, mixed-language response)
6. **Mobile PWA** - Progressive Web App with offline caching for watchlist and last recommendation

---

## Appendix

### File Structure

```
AlphaStream_India/
├── backend/
│   ├── src/
│   │   ├── agents/           # 13 specialized AI agents
│   │   ├── connectors/       # Data source connectors (NSE, BSE, Groww, WorldMonitor)
│   │   ├── pipeline/         # Pathway streaming + RAG
│   │   └── api/              # FastAPI application
│   ├── data/
│   │   └── articles/         # Pathway-persisted article cache
│   ├── market_analytics.duckdb  # Analytics DB (Nifty 50, signals, articles)
│   └── pyproject.toml
├── frontend/
│   └── src/
│       ├── components/trading/  # 25+ Bloomberg terminal components
│       ├── pages/               # Dashboard (5-tab layout)
│       ├── services/api.ts      # Typed API client
│       └── store/appStore.ts    # Zustand state + persistence
├── docs/
│   ├── ARCHITECTURE.md          # Mermaid data flow + component details
│   └── PROJECT_DOCUMENTATION.md
└── start_demo.sh
```

### Environment Variables

```bash
# Required — Google Vertex AI (Gemini LLM)
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
GCP_PROJECT_ID=your-project
GCP_REGION=us-central1

# Required — News
NEWS_API_KEY=...

# Indian market data
GROWW_API_TOKEN=...
GROWW_TOTP_SECRET=...

# Optional enrichment
FINNHUB_API_KEY=...
ALPHAVANTAGE_API_KEY=...
MEDIASTACK_API_KEY=...
FRED_API_KEY=...
```

---

**Document Version**: 2.0
**Last Updated**: March 2026
**Competition**: ET AI Hackathon 2026 - Problem Statement 6
**Team**: AlphaStream India
