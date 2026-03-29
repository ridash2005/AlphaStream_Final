# Deployment Guide

Step-by-step instructions for running AlphaStream India locally.

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | Required for the backend |
| uv | latest | Fast Python package manager (`pip install uv`) |
| Node.js | 20+ | Required for the frontend |
| Git | any | For cloning the repository |

## Quick Start

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd AlphaStream_India

# 2. Start the backend (installs deps, reads .env, launches on :8000)
cd backend && cp .env.example .env   # edit .env with your keys
./start.sh

# 3. In a second terminal, start the frontend
cd frontend && npm install && cp .env.example .env && npm run dev
```

Open `http://localhost:5173` in your browser. The frontend talks to the backend at `http://localhost:8000`.

## Backend Setup

### 1. Install dependencies

```bash
cd backend
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes | Path to GCP service-account JSON |
| `GCP_PROJECT_ID` | Yes | Your Google Cloud project ID |
| `GCP_REGION` | Yes | Vertex AI region (e.g. `us-central1`) |
| `VERTEX_MODEL` | Yes | Gemini model (e.g. `gemini-2.0-flash`) |
| `NEWS_API_KEY` | Yes | NewsAPI.org key (free tier: 100 req/day) |
| `FINNHUB_API_KEY` | No | Fallback news source |
| `ALPHAVANTAGE_API_KEY` | No | Fallback news source |
| `MEDIASTACK_API_KEY` | No | Fallback news source |
| `GROWW_API_TOKEN` | No | Groww JWT for live Indian market data |
| `FRED_API_KEY` | No | FRED key for macro signals |
| `ENABLE_PATHWAY` | No | `true` to activate streaming RAG |
| `ADAPTIVE_RAG_URL` | No | Pathway server URL (default: `http://localhost:8001`) |
| `DUCKDB_PATH` | No | DuckDB file path (default: `market_analytics.duckdb`) |
| `LOG_LEVEL` | No | `debug` / `info` / `warning` / `error` |

### 3. Start the server

```bash
# Recommended: use the start script
./start.sh

# Or start manually
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Verify

```bash
curl http://localhost:8000/health
```

Expected response: `{"status":"ok", ...}`

## Frontend Setup

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Configure environment

```bash
cp .env.example .env
```

Set `VITE_API_URL` to your backend address:

```
VITE_API_URL=http://localhost:8000
```

### 3. Start the dev server

```bash
npm run dev
```

Open `http://localhost:5173`.

### 4. Production build

```bash
npm run build      # outputs to frontend/dist/
npm run preview    # preview the production build locally
```

## Optional Features

### Pathway Streaming RAG

Enables low-latency document ingestion and retrieval via the Pathway pipeline.

```bash
# In backend/.env
ENABLE_PATHWAY=true
ADAPTIVE_RAG_URL=http://localhost:8001
```

Then start the Pathway server separately (see `backend/pathway_rag.yaml`).

### Groww Integration

Provides live NSE/BSE quotes and fundamentals for Indian stocks.

```bash
# In backend/.env
GROWW_API_TOKEN=<jwt-from-groww-app>
```

Extract the token from the Groww mobile app via DevTools → Network → `Authorization` header.

### FRED Macro Signals

Adds macroeconomic indicators (interest rates, CPI, GDP, yield curve) to the Global Intel tab.

```bash
# In backend/.env
FRED_API_KEY=<key-from-fred.stlouisfed.org>
```

Free API key available at [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html).

## Troubleshooting

### Port already in use

```
Error: address already in use :::8000
```

Kill the process occupying the port:

```bash
lsof -ti:8000 | xargs kill -9   # backend
lsof -ti:5173 | xargs kill -9   # frontend
```

### Missing API keys

The backend starts without most optional keys, but the following are required for core functionality:

- `GOOGLE_APPLICATION_CREDENTIALS` / `GCP_PROJECT_ID` — without these, the LLM agent will not start and `/recommend` returns 503
- `NEWS_API_KEY` — without this, no news articles are ingested; the RAG pipeline returns empty results

### DuckDB lock error

```
IOException: Could not set lock on file
```

Only one process can open the DuckDB file at a time. Stop any other backend instances before starting a new one:

```bash
pkill -f "uvicorn main:app"
```

### Frontend cannot reach backend

Ensure `VITE_API_URL` in `frontend/.env` matches the actual backend address. For Docker or remote deployments, use the container/host name instead of `localhost`.

### WebSocket disconnecting repeatedly

The frontend uses exponential back-off (up to 5 retries). If the WebSocket never connects, check that the backend is running and that no firewall or proxy is blocking the `/ws/stream/` path.
