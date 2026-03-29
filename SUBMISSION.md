# AlphaStream India — Hackathon Submission Package

**ET AI Hackathon 2026 — Problem Statement 6: AI for the Indian Investor**

---

## Submission Checklist

| Requirement | Status | Document |
|---|---|---|
| GitHub Repository | ✅ Complete | See `README.md` + commit history |
| 3-Minute Pitch Video | ⚠️ Recording needed | Script: `docs/VIDEO_DISCUSSION_SCRIPT.md` |
| Architecture Document | ✅ Complete | `docs/ARCHITECTURE.md` |
| Impact Model | ✅ Complete | `docs/impact_model.md` |

---

## 1. GitHub Repository

**Repository:** https://github.com/wildcraft958/AlphaStream_India

**What judges will find:**
- Full source code: 13 AI agents, 60+ REST endpoints, React 19 frontend with 35 components
- `README.md` — project overview, quick-start setup, full API reference
- `backend/` — Python FastAPI backend (agents, connectors, pipeline, NLQ)
- `frontend/` — React 19 + TypeScript + Tailwind Bloomberg-style terminal
- `worldmonitor/` — global market intelligence server
- `docker-compose.yml` — one-command deployment
- `backend/.env.example` — environment variable reference
- Commit history: 12+ meaningful commits showing incremental build from data layer → agents → frontend → polish

**Setup:** 3 commands — `uv sync` → `uvicorn src.api.app:app --port 8000` → `npm run dev`

---

## 2. 3-Minute Pitch Video

**Script:** [`docs/VIDEO_DISCUSSION_SCRIPT.md`](docs/VIDEO_DISCUSSION_SCRIPT.md)

The script is structured as a complete 3-minute walkthrough:

| Timestamp | Section | What to show |
|---|---|---|
| 0:00 – 0:30 | Problem + Solution | Hook: 14 Cr demat accounts, WhatsApp tips problem |
| 0:30 – 1:00 | Architecture | `docs/system_architecture.png` — 5-layer diagram |
| 1:00 – 2:15 | Live Demo | Dashboard: Overview → Signals → Global Intel → NLQ chat |
| 2:15 – 2:45 | Technical Highlights | Pathway features, India-first design |
| 2:45 – 3:00 | Conclusion | Impact metrics, closing statement |

**Pre-recording checklist:** See end of `docs/VIDEO_DISCUSSION_SCRIPT.md`

**To record:** Start backend + frontend, open http://localhost:5173, follow the script. Recommended tool: OBS Studio (free) or Loom.

---

## 3. Architecture Document

**Document:** [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

Covers all four required dimensions:

- **Agent roles** — Table of all 13 agents with input/output specification
- **Communication pattern** — NLQ LangGraph routing + WebSocket ticker pipeline
- **Tool integrations** — MCP servers, DuckDB, Pathway, yfinance, NSE/BSE APIs, Groww
- **Error handling logic** — 7 failure scenarios with recovery strategies

Supporting visuals (in `docs/`):
- `system_architecture.png` — full 5-layer system diagram
- `multi_agent_system.png` — agent coordination and fusion
- `herd_of_knowledge.png` — parallel multi-source news aggregation

---

## 4. Impact Model

**Document:** [`docs/impact_model.md`](docs/impact_model.md)

Quantified estimates with stated assumptions:

| Impact Area | Estimate | Method |
|---|---|---|
| Time saved per user | ₹2.19L/year | 1.75 hrs/day × ₹500/hr × 250 days |
| Alpha generated per user | ₹54,000/year | 2-3 signals/month × 60% accuracy × ₹3,000 |
| Risk reduction | 15% behavioral loss reduction | Signal-based early warning |
| ET Markets revenue (Year 1) | ₹53.7 Cr/year | 3 Cr users × 0.3% conversion × ₹999/month |

All assumptions explicitly stated. Back-of-envelope math in the document.

---

## Diagrams Index

| File | Description |
|---|---|
| `docs/system_architecture.png` | Full 5-layer architecture |
| `docs/multi_agent_system.png` | 13-agent coordination |
| `docs/herd_of_knowledge.png` | Parallel news aggregation |
| `docs/ARCHITECTURE.md` | Technical deep-dive with Mermaid diagrams |

---

## Key Numbers for Judges

- **13 AI agents** — each specializes in one analytical dimension
- **<2 seconds** — news article to updated recommendation (Pathway streaming)
- **60+ REST endpoints** — production-grade API
- **7-node LangGraph pipeline** — NLQ with Text2SQL (not hallucination)
- **5-year backtest** — all signals validated with win rates
- **14 Cr+ target users** — every Indian demat account holder
