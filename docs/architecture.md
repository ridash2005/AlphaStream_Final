# AlphaStream India - Architecture Document

## System Overview

AlphaStream India is an AI-powered investment intelligence platform for Indian retail investors. It ingests data from 6+ Indian market sources in real-time, processes it through 11 specialized AI agents, and delivers actionable signals via a Bloomberg-style React dashboard with natural language query capabilities.

## Agent Roles

| Agent | Role | Input | Output |
|---|---|---|---|
| **SentimentAgent** | Analyze market sentiment from news | Retrieved articles | sentiment_score (-1 to +1), label |
| **TechnicalAgent** | Calculate RSI, SMA, trend signals | yfinance .NS data | signal (BUY/HOLD/SELL), indicators |
| **RiskAgent** | Assess volatility, position sizing | Historical prices | risk_level, stop_loss, position_size |
| **DecisionAgent** | Synthesize final recommendation | All agent outputs | recommendation, confidence, reasoning |
| **PatternAgent** | Detect chart patterns | 6mo OHLCV data | patterns with confidence + explanation |
| **BacktestAgent** | Validate signals historically | 5yr OHLCV data | win_rate, avg_return per horizon |
| **FilingAgent** | Classify BSE/NSE filings | Announcement text | materiality, sentiment, key_facts |
| **FlowAgent** | Analyze FII/DII flow patterns | NSDL/NSE flow data | streak detection, divergence |
| **InsiderAgent** | Analyze SAST/PIT trades | NSE insider data | insider_score, key_transactions |
| **ChartAgent** | Generate price charts | yfinance data | PNG chart with annotations |
| **ReportAgent** | Generate PDF reports | All agent outputs | Comprehensive PDF report |

## Communication Pattern

```
User Query → NLQ Router (LangGraph)
                ├→ SIGNAL/INSIDER/FLOW → Pre-defined SQL → DuckDB → Narrate
                └→ AD_HOC → Text2SQL Pipeline:
                     Schema Link → Query Plan → SQL Generate → Guardrails → Execute → Narrate

User Ticker → WebSocket Stream
                → Sentiment → Technical → Risk → Decision → Stream Updates
```

Agents communicate via **shared state** (LangGraph AgentState). The NLQ agent uses **Command routing** to direct queries to the appropriate processing path. The ticker-based pipeline uses **sequential orchestration** with WebSocket progress callbacks.

## Tool Integrations

| Tool | Purpose | Transport |
|---|---|---|
| **market_data_server** (MCP) | Stock quotes, signals, sector heatmap | stdio |
| **signal_server** (MCP) | Threshold alerts, FII streak detection | stdio |
| **portfolio_server** (MCP) | Holdings P&L, portfolio signals | stdio |
| **DuckDB** | Analytics queries (Text2SQL target) | Direct connection |
| **Pathway** | Real-time news streaming + Adaptive RAG | Background thread |
| **yfinance** | Historical OHLCV data | HTTP |
| **NSE/BSE API** | Insider trades, filings, FII/DII | HTTP + cookies |
| **Groww API** | Stock search, fundamentals | JWT + TOTP |

## Error Handling

| Failure | Recovery |
|---|---|
| **Pathway server down** | UnifiedRAGService falls back to Manual RAG pipeline |
| **NSE API blocked** | yfinance .NS suffix as fallback for price data |
| **LLM timeout** | Heuristic fallback in DecisionAgent, PatternAgent returns empty |
| **Text2SQL generates bad SQL** | Correction loop: classify error → LLM fix → retry (max 2) |
| **DuckDB query timeout** | Hard 30s timeout, 5000 row cap, error returned to user |
| **MCP server crash** | Agent degrades gracefully - direct DuckDB queries |
| **Guardrail blocks DDL/DML** | Regex hard-stop, query rejected before execution |

## Data Flow

1. **Ingestion**: Pathway streams news from ET Markets, MoneyControl, LiveMint RSS every 30s
2. **Storage**: Articles → `data/articles/` (filesystem) for Pathway Adaptive RAG
3. **Analytics DB**: DuckDB with Nifty 50 prices (5yr), signals, insider trades, FII/DII flows
4. **Query**: NLQ Text2SQL generates SELECT queries against DuckDB views
5. **Signals**: PatternAgent + BacktestAgent detect patterns and validate historically
6. **Fusion**: Alpha Score combines all signals with configurable weights
7. **Delivery**: SSE streaming for NLQ, WebSocket for ticker updates, REST for snapshots
