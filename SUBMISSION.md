# AlphaStream India — Hackathon Submission

**ET AI Hackathon 2026 — Problem Statement 6: AI for the Indian Investor**

---

## Submission Checklist

| Requirement | Status | Location |
|---|---|---|
| GitHub Repository | Done | `README.md` + commit history |
| Architecture Document | Done | `docs/ARCHITECTURE.md` |
| Impact Model | Done | `docs/impact_model.md` |

---

## 1. GitHub Repository

**Repository:** https://github.com/wildcraft958/AlphaStream_India

**What judges will find:**
- Full source code: 13 AI agents, 60+ REST endpoints, React 19 frontend with 30+ components
- `README.md` — project overview, quick-start setup, full API reference
- `backend/` — Python FastAPI backend (agents, connectors, pipeline, NLQ)
- `frontend/` — React 19 + TypeScript + Tailwind Bloomberg-style terminal
- `worldmonitor/` — global market intelligence module
- `docker-compose.yml` — one-command deployment
- `backend/.env.example` — environment variable reference

**Setup:** 3 commands — `uv sync` -> `./start.sh` -> `npm run dev`

---

## 2. Architecture Document

**Document:** [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

Covers:

- **System overview** — 5-layer architecture (data sources, Pathway streaming, 13-agent reasoning, DuckDB analytics, React terminal)
- **Pathway integration** — Adaptive RAG with geometric retrieval, 12+ Pathway features used
- **Agent specifications** — All 13 agents with input/output/technology
- **NLQ pipeline** — LangGraph 7-node graph with Text2SQL, guardrails, and SSE streaming
- **Data flow** — Mermaid diagram showing end-to-end pipeline
- **API layer** — 60+ REST endpoints, WebSocket, SSE
- **Performance** — <2s data-to-update latency, ~7s full recommendation

Supporting diagrams (in `docs/`):
- `system_architecture.png` — full 5-layer system diagram
- `multi_agent_system.png` — agent coordination and fusion
- `herd_of_knowledge.png` — parallel multi-source news aggregation

---

## 3. Impact Model

**Document:** [`docs/impact_model.md`](docs/impact_model.md)

Quantified estimates with stated assumptions:

| Impact Area | Estimate | Method |
|---|---|---|
| Time saved per user | INR 2.19L/year | 1.75 hrs/day x INR 500/hr x 250 days |
| Alpha generated per user | INR 54,000/year | 2-3 signals/month x 60% accuracy x INR 3,000 |
| Risk reduction | 15% behavioral loss reduction | Signal-based early warning |
| ET Markets revenue (Year 1) | INR 59.9 Cr/year | 50K premium users x INR 999/month x 12 |

All assumptions explicitly stated. Back-of-envelope math in the document.

---

## Key Numbers

- **13 AI agents** — each specializes in one analytical dimension
- **<2 seconds** — news article to updated recommendation (Pathway streaming)
- **60+ REST endpoints** — production-grade API
- **7-node LangGraph pipeline** — NLQ with Text2SQL (not hallucination)
- **5-year backtest** — all signals validated with win rates
- **14 Cr+ target users** — every Indian demat account holder
