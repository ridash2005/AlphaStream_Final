# AlphaStream Backend

Python backend for AlphaStream Live AI trading system.

## Components

- **Agents**: Sentiment, Technical, Risk, Decision, Insider, Chart, Report
- **Connectors**: NewsAPI, SEC EDGAR
- **Pipeline**: RAG (Chunking, Embedding, Retrieval, Reranking)
- **API**: FastAPI endpoints + WebSocket streaming

## Setup

```bash
cd backend
uv sync
uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```

## Environment

Copy `.env.example` to `.env` and configure:
- `OPENROUTER_API_KEY` - LLM access
- `NEWS_API_KEY` - Real-time news

## Testing

```bash
uv run pytest tests/ -v
```
