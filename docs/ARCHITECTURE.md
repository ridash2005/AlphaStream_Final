# AlphaStream India — Architecture

Detailed technical architecture for the AlphaStream India AI trading terminal.

---

## System Overview

AlphaStream India implements a **streaming RAG + multi-agent** architecture focused on the Indian equity market (NSE/BSE). The system is designed for:

1. **Real-time data ingestion** — Pathway streaming, <2s latency from news to recommendation
2. **Incremental updates** — Knowledge base updates continuously via Adaptive RAG
3. **Explainable AI** — Every recommendation traces back to sources, agent scores, and signals
4. **India-first context** — ₹ currency, IST timezone, NSE/BSE tickers, Nifty 50 universe

---

## Data Flow

```mermaid
graph LR
    subgraph "Indian Data Sources"
        A1[NewsAPI / RSS]
        A2[NSE / BSE API]
        A3[Groww API]
        A4[NSDL FII/DII]
        A5[FRED Macro]
    end

    subgraph "Global Data Sources"
        G1[WorldMonitor]
        G2[CNN Fear&Greed]
        G3[yfinance Indices]
    end

    subgraph "Ingestion Layer"
        B1[Pathway Streaming]
        B2[Threat Classifier]
        B3[DuckDB Ingest]
    end

    subgraph "Analytics Layer (DuckDB)"
        C1[fact_articles]
        C2[fact_signals]
        C3[v_stock_screener]
        C4[dim_stocks Nifty50]
    end

    subgraph "Agent System (13 agents)"
        D1[Sentiment]
        D2[Technical + RSI/SMA]
        D3[Risk]
        D4[Decision]
        D5[Flow + Anomaly]
        D6[Pattern + Backtest]
    end

    subgraph "API Layer (FastAPI)"
        E1[Market Router]
        E2[Global Router]
        E3[NLQ Router]
        E4[WebSocket]
    end

    subgraph "React Terminal (5 tabs)"
        F1[Overview: Chart+Fundamentals]
        F2[Signals: Screener+Radar]
        F3[Global: Crypto+FX+Sectors]
        F4[Company: Filings+News]
        F5[Portfolio: P&L]
    end

    A1 --> B1
    A2 --> B1
    B1 --> B2
    B2 --> B3
    B3 --> C1
    A2 --> D2
    A3 --> D2
    A4 --> D5
    A5 --> D4
    G1 --> E2
    G2 --> E2
    G3 --> E2
    C1 --> D1
    C2 --> D6
    C3 --> E1
    C4 --> E1
    D1 --> D4
    D2 --> D4
    D3 --> D4
    D5 --> D4
    D4 --> E4
    E1 --> F1
    E1 --> F2
    E2 --> F3
    E1 --> F4
    E1 --> F5
    B2 --> D4
    D1 & D3 & D4 --> D5
    D5 --> E1 & E2
    D1 & D2 & D3 & D4 --> E3
```

---

## Component Architecture

### 1. Pathway Streaming Engine

![AlphaStream System Architecture](system_architecture.png)

AlphaStream leverages **Pathway** as the core streaming engine. Our implementation demonstrates comprehensive feature usage:

#### Pathway Features Used

| Feature | Location | Purpose |
|---------|----------|---------|
| `pw.Schema` | `news_connector.py`, `pathway_tables.py` | Type-safe data schemas |
| `pw.Table` | `pathway_tables.py` | Streaming market data tables |
| `pw.io.python.ConnectorSubject` | `news_connector.py` | Custom multi-source news polling |
| `pw.io.subscribe` | `app.py` | Real-time callbacks on data events |
| `pw.run` | `app.py` | Background Pathway engine |
| `pw.apply` | `pathway_tables.py` | UDF for ticker extraction, labels |
| `pw.filter` | `pathway_tables.py` | Alert generation on sentiment spikes |
| `pw.reducers` | `pathway_tables.py` | Aggregations (avg, count, max, min) |

#### "Herd of Knowledge" Architecture

![Herd of Knowledge](herd_of_knowledge.png)

Our multi-source news aggregator fetches from 5 sources **in parallel**:

```python
# ThreadPoolExecutor for parallel API calls
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(fetch_source, src): src for src in self.sources}
```

- **NewsAPI** - Breaking headlines
- **Finnhub** - Company-specific news (60 calls/min free)
- **Alpha Vantage** - Sentiment-tagged articles (500 calls/day free)
- **MediaStack** - Global business news (500 calls/month free)
- **RSS Feeds** - Unlimited, free fallback

**Result**: 40+ unique articles per refresh cycle, no single point of failure.

```python
# Pathway integration in app.py
import pathway as pw

news_table = create_news_table(refresh_interval=60)
pw.io.subscribe(news_table, on_new_article_callback)
pw.run()  # Background thread
```

### 2. RAG Pipeline

**Chunking Strategy:**
- Sentence-based with semantic boundaries
- ~300 tokens per chunk for optimal retrieval
- Metadata enrichment (source, date, tickers)

**Retrieval:**
- Dense retrieval (sentence-transformers embeddings)
- Sparse retrieval (BM25)
- Reciprocal Rank Fusion (RRF) for combining scores
- Cross-encoder reranking (optional)

### 3. Agent System

Each agent is a specialized LangChain chain:

| Agent | Input | Output | Technology |
|-------|-------|--------|------------|
| Sentiment | Articles | Score (-1 to +1), Label | LangChain + OpenAI |
| Technical | Ticker | Score, RSI, SMA | yfinance + numpy |
| Risk | Technical data | Position size, Stop loss | Volatility calculation |
| Insider | Ticker | Score, Transactions | edgartools + LLM |
| Decision | All agents | BUY/HOLD/SELL | LangChain + OpenAI |

**Agent Communication:**
```
Sentiment ─┐
           │
Technical ─┼─► Decision Agent ─► Recommendation
           │
Risk ──────┤
           │
Insider ───┘
```

### 4. API Layer

FastAPI with:
- **REST endpoints** for synchronous queries
- **WebSocket** for real-time pushes
- **CORS** enabled for frontend
- **Connection Manager** for broadcast

### 5. Frontend

React SPA with:
- **Zustand** for state management
- **WebSocket** for live updates
- **Shadcn UI** components
- **Tailwind CSS** styling

---

## Security Considerations

1. **API Keys** - Never committed to git (`.gitignore`)
2. **Rate Limiting** - SEC fair access (10 req/sec)
3. **Input Validation** - Pydantic models
4. **Error Handling** - Graceful fallbacks

---

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Article ingestion | <100ms |
| Full recommendation | ~10s (LLM bound) |
| Chart generation | ~2s |
| PDF report | ~15s |
| WebSocket latency | <50ms |

---

## Deployment Options

### Local Development
```bash
uv run uvicorn src.api.app:app --reload
```

### Docker
```bash
docker-compose up
```

### Production
- Use gunicorn with uvicorn workers
- Enable persistence for fault tolerance
- Configure logging for monitoring
