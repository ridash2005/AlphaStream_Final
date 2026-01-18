# AlphaStream Live AI

**Real-Time Financial Intelligence Powered by Pathway Streaming Engine**

AlphaStream is a production-grade AI trading system that solves the "stale knowledge" problem in financial analysis. It combines **real-time news ingestion**, **SEC EDGAR filings**, **multi-agent reasoning**, and **live visualization** to deliver instant, explainable trading recommendations.

Built for **DataQuest 2026** hackathon using the [Pathway](https://pathway.com/) streaming framework.

---

## 🎯 Problem Statement

Traditional AI systems suffer from knowledge cutoff—they can't react to breaking news or regulatory filings. AlphaStream demonstrates **Live AI**:
- Ingests news articles in real-time
- Updates recommendations in **<2 seconds** when new data arrives
- Incorporates SEC insider trading data
- Generates professional PDF reports

---

## 🚀 Key Features

### Real-Time Data Pipeline
- **Pathway Streaming Engine** - Incremental processing, no batch jobs
- **NewsAPI Integration** - Live financial news polling
- **SEC EDGAR Connector** - Form 4 insider trading filings

### Multi-Agent Reasoning System
| Agent | Function |
|-------|----------|
| **Sentiment Agent** | LLM-powered news sentiment analysis |
| **Technical Agent** | RSI, SMA calculations from yfinance |
| **Risk Agent** | Volatility-based position sizing |
| **Insider Agent** | SEC Form 4 transaction analysis |
| **Chart Agent** | 7-day price charts with 24h highlighting |
| **Report Agent** | PDF generation with charts & tables |
| **Decision Agent** | Final BUY/HOLD/SELL recommendation |

### Bloomberg-Style Dashboard
- Real-time sentiment heatmap
- Agent consensus radar chart
- Insider activity panel
- One-click PDF report generation

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|------------|
| **Streaming Engine** | Pathway |
| **Backend** | FastAPI, Python 3.11 |
| **LLM** | LangChain, OpenRouter (Claude/Gemma) |
| **Market Data** | yfinance, edgartools |
| **PDF Reports** | ReportLab, Matplotlib |
| **Frontend** | React 18, Vite, Tailwind CSS, Shadcn |
| **State** | Zustand |

---

## ⚡ Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- API Keys: OpenRouter, NewsAPI

### 1. Clone & Setup
```bash
cd "Data Quest"

# Install Python dependencies (using uv)
uv sync

# Install frontend dependencies
cd frontend && npm install && cd ..
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your API keys:
# - OPENROUTER_API_KEY
# - NEWS_API_KEY
```

### 3. Run the System

**Terminal 1: Backend**
```bash
uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```

**Terminal 2: Frontend**
```bash
cd frontend && npm run dev
```

Access dashboard at **http://localhost:5173**

---

## 📡 API Endpoints

### Core Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/recommend` | Get trading recommendation |
| `GET` | `/health` | System health check |
| `GET` | `/articles/{ticker}` | Get related articles |
| `POST` | `/ingest` | Inject test article |

### SEC EDGAR Endpoints (Stage 5)
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/insider/{ticker}` | Insider trading activity |
| `GET` | `/chart/{ticker}` | Price comparison chart |
| `POST` | `/report/{ticker}` | Generate PDF report |

### WebSocket
| Path | Description |
|------|-------------|
| `/ws/stream/{ticker}` | Real-time recommendation updates |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            AlphaStream Architecture                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────────────────┐
│  │   NewsAPI   │────►│   Pathway   │────►│          RAG Pipeline          │
│  │   Stream    │     │  Connector  │     │  (Chunk → Embed → Index)       │
│  └─────────────┘     └─────────────┘     └─────────────────────────────────┘
│                                                      │
│  ┌─────────────┐                                     ▼
│  │ SEC EDGAR   │────────────────────────►┌─────────────────────────────────┐
│  │   (Form 4)  │                         │        AGENT SYSTEM             │
│  └─────────────┘                         │                                 │
│                                          │  ┌──────────┐  ┌──────────┐    │
│  ┌─────────────┐                         │  │Sentiment │  │Technical │    │
│  │  yfinance   │────────────────────────►│  │  Agent   │  │  Agent   │    │
│  │ (Prices)    │                         │  └────┬─────┘  └────┬─────┘    │
│  └─────────────┘                         │       │             │          │
│                                          │  ┌────▼─────┐  ┌────▼─────┐    │
│                                          │  │ Insider  │  │   Risk   │    │
│                                          │  │  Agent   │  │  Agent   │    │
│                                          │  └────┬─────┘  └────┬─────┘    │
│                                          │       │             │          │
│                                          │       └──────┬──────┘          │
│                                          │              ▼                  │
│                                          │       ┌──────────────┐         │
│                                          │       │   Decision   │         │
│                                          │       │    Agent     │         │
│                                          │       └──────┬───────┘         │
│                                          └──────────────┼─────────────────┘
│                                                         │
│  ┌─────────────────────────────────────────────────────▼───────────────────┐
│  │                         FastAPI Backend                                  │
│  │    /recommend    /insider    /chart    /report    /ws/stream             │
│  └─────────────────────────────────────────────────────────────────────────┘
│                                          │
│  ┌─────────────────────────────────────────────────────▼───────────────────┐
│  │                      React Dashboard (Vite)                              │
│  │   TickerSearch │ RecommendationCard │ Heatmap │ Radar │ InsiderActivity │
│  └─────────────────────────────────────────────────────────────────────────┘
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
Data Quest/
├── src/
│   ├── agents/
│   │   ├── sentiment_agent.py   # LangChain sentiment analysis
│   │   ├── technical_agent.py   # RSI, SMA from yfinance
│   │   ├── risk_agent.py        # Volatility & position sizing
│   │   ├── decision_agent.py    # Final recommendation (LLM)
│   │   ├── insider_agent.py     # SEC Form 4 analysis
│   │   ├── chart_agent.py       # Matplotlib charts
│   │   └── report_agent.py      # ReportLab PDF
│   ├── connectors/
│   │   ├── news_connector.py    # NewsAPI + Pathway
│   │   └── sec_connector.py     # SEC EDGAR (edgartools)
│   ├── pipeline/
│   │   ├── rag_core.py          # RAG pipeline
│   │   ├── chunking.py          # Adaptive chunking
│   │   └── retrieval.py         # Hybrid retrieval
│   └── api/
│       └── app.py               # FastAPI application
├── frontend/
│   └── src/
│       ├── App.tsx              # Main dashboard
│       └── components/trading/  # UI components
├── reports/                     # Generated PDF reports
├── tests/                       # pytest tests
└── pyproject.toml              # Dependencies
```

---

## 🧪 Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Test real-time dynamism
uv run scripts/inject_article.py "Breaking News" "Content here"
# Watch recommendation change in <2s
```

---

## 🐳 Docker Deployment

```bash
docker-compose up --build
```

Access at http://localhost:8000 (API) and http://localhost:5173 (Dashboard)

---

## 📊 Demo: Proving Real-Time Dynamism

1. Start the system
2. Search for "AAPL" → Note recommendation
3. Inject bearish article:
   ```bash
   uv run scripts/inject_article.py "Apple Faces Lawsuit" "Major legal trouble..."
   ```
4. Watch recommendation change in **<2 seconds**
5. Generate PDF report with updated analysis

---

## 📝 License

MIT License. Built for DataQuest 2026 Hackathon.

---

## 🙏 Acknowledgments

- **Pathway** - Streaming engine powering real-time RAG
- **OpenRouter** - LLM API access
- **edgartools** - SEC EDGAR data access
