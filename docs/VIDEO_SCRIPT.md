# AlphaStream India - Demo Video Script
## ET AI Hackathon 2026 | ~4 Minutes

Natural talking points. Don't read verbatim - use these as a guide and let the screen do the talking.

---

## Before You Record

Start the app and do one dry run:

```bash
# Terminal 1
cd backend && ./start.sh

# Terminal 2
cd frontend && npm run dev
```

- Open http://localhost:5173
- Log in as judge@etmedia.com
- RELIANCE should load on Overview tab
- Toggle Indicators on the chart (confirm RSI + SMA lines appear)
- Open NLQ panel, type any question, confirm it responds
- Switch through all 5 tabs to make sure they load

Open a second terminal at the project root, run `./scripts/demo_live_sentiment.sh bearish` and confirm the recommendation updates on the dashboard without refreshing. Once everything works, start recording (OBS / Loom / any screen recorder).

---

## PART 1 - The Problem (0:00 - 0:25)

**[Screen: show the landing page or a simple title card]**

"India has over 14 crore demat accounts. That's 14 crore people who are in the stock market. But most of them are researching stocks the same way - scrolling through WhatsApp groups, watching YouTube tips, spending two hours a day trying to figure out what to buy.

Meanwhile, institutional investors have Bloomberg terminals, real-time feeds, and teams of analysts. There's a massive gap. That's what AlphaStream India solves."

---

## PART 2 - What We Built (0:25 - 0:50)

**[Screen: switch to the live dashboard, Overview tab with RELIANCE loaded]**

"This is AlphaStream India. Think of it as a Bloomberg terminal designed from scratch for the Indian retail investor.

It's not a chatbot wrapper around GPT. It's a full analytics platform. Behind this interface there are 13 specialized AI agents, a streaming data pipeline built on Pathway, and a DuckDB analytics engine - all working together to give you real-time, grounded, actionable intelligence."

**[Screen: briefly point at the architecture diagram `docs/system_architecture.png` - keep this under 10 seconds]**

"Five layers - data sources at the bottom, Pathway streaming engine, 13-agent reasoning, DuckDB analytics, and this React terminal on top. Let me show you what each piece actually does."

---

## PART 3 - Live Demo (0:50 - 2:45)

This is the core of the video. Slow down, let the UI breathe on screen.

### 3A - Overview Tab (0:50 - 1:20)

**[Screen: Overview tab, RELIANCE chart visible]**

"When I search for RELIANCE, the system kicks off all 13 agents simultaneously. Watch the loading - you can see each agent reporting in: Sentiment Agent analyzing news... Technical Agent calculating RSI and moving averages... Risk Agent, Flow Agent checking FII/DII data..."

**[Screen: point at the recommendation card once it loads]**

"Here's the final verdict - BUY, HOLD, or SELL with a confidence score. This isn't one LLM call. This is the Decision Agent fusing inputs from Sentiment, Technical, Risk, Flow, and Global Market context into a single recommendation."

**[Screen: click Indicators toggle on the chart]**

"The candlestick chart runs on lightweight-charts. I can toggle technical overlays - SMA 20, SMA 50, and an RSI sub-chart. These are calculated from real NSE OHLCV data, not mocked."

**[Screen: scroll down to show Fundamentals and Anomaly panels]**

"Below we have live fundamentals pulled from Groww - PE ratio, PB, ROE, 52-week range. And anomaly detection using River ML that flags unusual price or volume moves."

### 3B - Signals Tab (1:20 - 1:45)

**[Screen: click Signals tab]**

"Signals tab is where you hunt for opportunities. This stock screener queries a pre-aggregated DuckDB view. I can filter by sector..."

**[Screen: select a sector from the dropdown]**

"...by direction - bullish or bearish..."

**[Screen: click bullish filter]**

"...and by minimum alpha score. Alpha score is our composite signal strength from 0 to 100 - it combines pattern detection, backtest win rates, and agent confidence."

**[Screen: click on any stock row in the screener]**

"Click any stock and it loads on the Overview tab instantly. The sector heatmap and insider activity panels give you the broader picture - which sectors are hot, who's buying inside the company."

### 3C - Global Intel Tab (1:45 - 2:05)

**[Screen: click Global Intel tab]**

"India doesn't trade in isolation. This tab pulls live data from our WorldMonitor integration."

**[Screen: show crypto section, then click Currencies tab]**

"Crypto prices with INR equivalents. Currency pairs - notice when INR weakens, the system annotates it: 'Rupee weakening, higher import costs.' This context feeds directly into the Decision Agent."

**[Screen: point at Fear & Greed gauge and Macro Signals]**

"Fear and Greed index, macro signals from FRED - yield curve, CPI, unemployment. And at the bottom, a geopolitical risk score specifically calibrated for India. All of this is wired into every recommendation the system makes."

### 3D - NLQ Agent (2:05 - 2:35)

**[Screen: click the NLQ button in bottom-right corner]**

"This is the part I'm most excited about. Open the NLQ panel and ask anything in plain English."

**[Screen: type "Top 5 stocks by alpha score" and hit Enter]**

"Watch the thought process - it goes through a 7-node LangGraph pipeline. First the input guardrail checks if this is a valid market question. Then the router decides this is a signal query. It generates SQL, runs it against DuckDB, and the narrator turns the raw data into a human-readable answer."

**[Screen: point at the SQL preview and the chart that renders]**

"See the SQL it generated? That's real. The answer is grounded in actual data from our analytics store - not LLM hallucination. And it auto-generates a chart from the results."

**[Screen: click Expand button to show full chart view]**

"I can expand to full view for better charts. And notice the suggested follow-up questions - they change based on which tab I'm on. The NLQ agent is context-aware."

### 3E - Live Sentiment Shift (2:35 - 3:05)

**This is the "wow" moment. Practice this once before recording.**

**[Screen: Overview tab showing RELIANCE with current recommendation (e.g. HOLD or BUY)]**

"Now here's the real test of a live system. I'm going to inject a breaking news article and we'll watch the recommendation change in real time."

**[Screen: switch to a terminal window, already open and ready. Run the script:]**

```bash
./scripts/demo_live_sentiment.sh bearish
```

"I just posted a bearish breaking news article - SEBI probe, FII selling, analyst downgrade. Watch the dashboard..."

**[Screen: switch back to the browser. Wait ~10 seconds. The recommendation card will re-animate with new data.]**

"There it is. The sentiment shifted. The recommendation changed. The key factors updated. That's a real news article flowing through the Pathway pipeline, hitting all 13 agents, and pushing a new recommendation to the browser via WebSocket. No page refresh. No re-search. Fully automatic."

**[Optional: if time permits, run the bullish script too]**

```bash
./scripts/demo_live_sentiment.sh bullish
```

"And if I inject bullish news... watch it swing back. This is what Pathway streaming makes possible - live AI, not stale AI."

### 3F - Portfolio (3:05 - 3:15)

**[Screen: click Portfolio tab, show the Groww import button]**

"Quick look at portfolio management - I can import holdings directly from Groww and track live P&L. The system gives portfolio-aware alerts too."

---

## PART 4 - What Makes This Different (3:15 - 3:40)

**[Screen: back on Overview tab with the shifted recommendation visible]**

"Let me be clear about what separates this from a typical hackathon project.

First - **Pathway streaming**. You just saw it. A news article arrived and the recommendation updated automatically. That's not batch processing. That's live AI.

Second - **13 agents, not one GPT call**. Sentiment, Technical, Risk, Flow, Pattern, Backtest, Insider, Anomaly - each one is a specialist. The Decision Agent fuses them all. You get an explainable recommendation, not a black box.

Third - **Text2SQL, not hallucination**. When you ask the NLQ agent a question, it writes SQL, executes it against real data, and narrates the result. Every answer has a source.

Fourth - **India-first**. Rupees, IST timezone, NSE/BSE tickers, FII/DII tracking, BSE corporate filings, Groww integration. This isn't a global tool localized - it's built for the Indian market from day one."

---

## PART 5 - Closing (3:40 - 3:55)

**[Screen: show the full dashboard one more time]**

"14 crore demat accounts. Most of them flying blind. AlphaStream India gives every retail investor the same intelligence that institutions pay lakhs for - real-time, AI-powered, and completely free.

This is AlphaStream India. Thank you."

---

## Tips for Recording

- **Pace**: Don't rush. The UI is visually rich - let the screen breathe for 2-3 seconds between clicks.
- **Mouse**: Move slowly and deliberately. Circle important elements with your cursor instead of clicking wildly.
- **Narration**: Talk TO the viewer, not at the screen. "See this? That's real SQL being generated" is better than "the system generates SQL."
- **Errors**: If something takes a moment to load, narrate it: "The agents are working... there it is." Makes it feel live.
- **Length**: Aim for 3:45-4:00. If you're over, shorten Part 4 (the differentiators are already shown in the demo). The live sentiment shift is the money shot - don't cut it.
