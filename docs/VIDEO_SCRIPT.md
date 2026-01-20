# AlphaStream Live AI - Video Demonstration Script
## DataQuest 2026 Hackathon | 3-Minute Video Demo

---

## 🎬 Pre-Recording Checklist

Before recording, ensure you have:
- [ ] Backend running: `cd backend && uv run uvicorn src.api.app:app --port 8000`
- [ ] Frontend running: `cd frontend && npm run dev`
- [ ] Dashboard open at http://localhost:5173
- [ ] Terminal ready for demo commands
- [ ] API keys configured in `.env`

---

## 📋 Video Timeline (3 Minutes)

| Timestamp | Section | Duration |
|-----------|---------|----------|
| 0:00 - 0:30 | Introduction & Problem Statement | 30s |
| 0:30 - 1:00 | Architecture Overview | 30s |
| 1:00 - 2:15 | Live Demo (Real-Time Proof) | 75s |
| 2:15 - 2:45 | Technical Deep Dive | 30s |
| 2:45 - 3:00 | Conclusion | 15s |

---

## 🎤 Script

### SECTION 1: Introduction (0:00 - 0:30)

**[Screen: Title slide with AlphaStream logo]**

> **Speaker:**
> "Hi, I'm [Name] from Team [Team Name]. Today I'm presenting AlphaStream Live AI - a real-time trading intelligence system powered by Pathway's streaming framework.
>
> **The Problem:** Traditional AI systems suffer from 'stale knowledge' - they can't react to breaking news or regulatory filings. By the time they process information, the market has already moved.
>
> **Our Solution:** AlphaStream delivers instant, explainable trading recommendations that update in under 2 seconds when new data arrives."

---

### SECTION 2: Architecture Overview (0:30 - 1:00)

**[Screen: Show architecture diagram - docs/system_architecture.png]**

> **Speaker:**
> "Let me walk you through our architecture. AlphaStream has three core layers:
>
> **First: Data Ingestion** - Our 'Herd of Knowledge' aggregator fetches news from 5 sources in parallel: NewsAPI, Finnhub, Alpha Vantage, MediaStack, and RSS feeds. No single point of failure.

**[Screen: Show docs/herd_of_knowledge.png]**

> **Second: Pathway Streaming Engine** - This is the heart of our system. We use Pathway's official `xpacks.llm` with Adaptive RAG. It features geometric retrieval - starting with 2 documents and expanding only when needed, saving 40% on token costs.

**[Screen: Show docs/multi_agent_system.png]**

> **Third: Multi-Agent Reasoning** - Seven specialized AI agents: Sentiment, Technical, Risk, Insider, Chart, Report, and Decision. They work together to generate BUY, HOLD, or SELL recommendations."

---

### SECTION 3: Live Demo - Real-Time Proof (1:00 - 2:15)

**[Screen: Show frontend dashboard + terminal side by side]**

> **Speaker:**
> "Now let's prove this works in real-time. I have the dashboard open, showing the current state."

#### Step 3.1: Initial Recommendation (1:00 - 1:20)

**[Action: Click on "Search" and enter "AAPL"]**

> **Speaker:**
> "I'm searching for Apple stock. The system queries all seven agents...
> [Wait for results]
> We get a recommendation of [READ THE ACTUAL RESULT]. Notice the sentiment score, technical indicators, and confidence level."

**[Highlight the recommendation panel on dashboard]**

---

#### Step 3.2: Inject Breaking News (1:20 - 1:40)

**[Action: Open terminal, run inject command]**

> **Speaker:**
> "Now here's where it gets interesting. I'm going to inject breaking bearish news into the system."

**[Type/Run command:]**
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"title":"Apple Faces Major Regulatory Investigation","content":"BREAKING: Apple is facing a significant regulatory investigation that could result in billions in fines. Multiple analysts are issuing sell recommendations.","source":"Breaking News","tickers":["AAPL"]}'
```

> **Speaker:**
> "This article is now being ingested into our Pathway RAG pipeline..."

---

#### Step 3.3: Observe Real-Time Update (1:40 - 2:00)

**[Screen: Focus on dashboard - watch for WebSocket update]**

> **Speaker:**
> "Watch the dashboard closely. Within 2 seconds, you'll see the sentiment change reflected automatically via WebSocket.
>
> [Point to changes]
> There! The sentiment score dropped from [OLD] to [NEW]. The recommendation has changed from [OLD] to [NEW]. 
>
> This is **Live AI** - no refresh needed, no batch processing. The system responded in under 2 seconds."

---

#### Step 3.4: Generate PDF Report (2:00 - 2:15)

**[Action: Click "Generate Report" button on dashboard, or run:]**
```bash
curl -X POST http://localhost:8000/report/AAPL
```

> **Speaker:**
> "We can also generate a professional PDF report with all agent analyses, charts, and the latest recommendation. The report includes SEC insider trading data, 7-day price charts, and the full reasoning chain."

**[Show generated PDF briefly if time permits]**

---

### SECTION 4: Technical Deep Dive (2:15 - 2:45)

**[Screen: Show code snippets or terminal output]**

> **Speaker:**
> "Under the hood, we're leveraging these key Pathway features:
>
> - **pw.io.python.ConnectorSubject** for custom streaming data ingestion
> - **pw.xpacks.llm.AdaptiveRAGQuestionAnswerer** with geometric retrieval strategy
> - **pw.io.subscribe** for real-time callbacks that trigger WebSocket broadcasts
> - **pw.indexing.UsearchKnnFactory** for fast vector similarity search
>
> The demo script we just ran also saved detailed proof to `demo_output.json` with timestamps, latencies, and all internal logs."

**[Optional: Quickly show demo_output.json structure]**

---

### SECTION 5: Conclusion (2:45 - 3:00)

**[Screen: Return to dashboard or summary slide]**

> **Speaker:**
> "To summarize, AlphaStream demonstrates:
>
> 1. **Streaming ingestion** from multiple news sources
> 2. **Real-time transformation** via Pathway Adaptive RAG
> 3. **Live output** within 2 seconds via WebSocket
>
> This is what 'Live AI' looks like - an AI that evolves with the market, not one that's stuck in the past.
>
> Thank you for watching!"

---

## 🎬 Recording Tips

### Do's:
- ✅ Speak clearly and at a moderate pace
- ✅ Keep the terminal and dashboard visible simultaneously (split screen)
- ✅ Point to specific UI elements when discussing them
- ✅ Pause briefly after running commands to let viewers see results
- ✅ Read actual values from the screen, don't guess

### Don'ts:
- ❌ Don't rush through the live demo - it's the most important part
- ❌ Don't read the script verbatim - use natural language
- ❌ Don't panic if something takes a moment - the latency is still impressive
- ❌ Don't exceed 3 minutes - practice with a timer!

---

## 📱 Screen Recording Setup

### Recommended Layout:
```
+----------------------------+----------------------------+
|                            |                            |
|     Dashboard (60%)        |     Terminal (40%)         |
|     http://localhost:5173  |     For curl commands      |
|                            |                            |
+----------------------------+----------------------------+
```

### Resolution:
- 1920x1080 (Full HD) recommended
- Ensure text is readable

### Recording Software:
- OBS Studio (free, cross-platform)
- Kazam (Linux)
- QuickTime (macOS)

---

## 🔄 Alternative: Using demo_pipeline.py

Instead of manual curl commands, you can run the automated demo:

```bash
python demo_pipeline.py --ticker AAPL --output demo_output.json
```

This script:
1. Checks backend health
2. Fetches initial recommendation
3. Injects bearish news
4. Shows recommendation change
5. Saves proof to JSON file

The output is beautifully formatted with Rich library and clearly shows the before/after comparison.

---

## 📊 Key Metrics to Mention

| Metric | Value |
|--------|-------|
| Article ingestion latency | <100ms |
| Full recommendation time | ~1.2s (LLM-bound) |
| WebSocket delivery | <50ms |
| **Total: Data → Update** | **<2 seconds** |
| Token savings (Adaptive RAG) | 40% vs fixed-k |

---

## 🏆 Judging Criteria Alignment

| Criterion | How We Demonstrate |
|-----------|-------------------|
| Real-time behavior | Breaking news → recommendation change in <2s |
| Streaming ingestion | Multiple parallel news sources via Pathway |
| Transformation | Pathway Adaptive RAG with multi-agent reasoning |
| Output/Action | WebSocket updates + PDF report generation |
| Working application | Live dashboard with full functionality |

---

## 📝 Backup Plan

If live demo fails:
1. Show pre-recorded screen capture of working demo
2. Walk through `demo_output.json` as proof
3. Show code structure and explain architecture

Always have `demo_output.json` ready with a successful run as backup evidence!

---

*Good luck with your recording! 🚀*
