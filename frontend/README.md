# AlphaStream India — Frontend

React + TypeScript single-page dashboard for Indian stock market analytics, providing AI-driven recommendations, global macro intelligence, portfolio management, and natural language querying via an integrated agent.

## Dashboard Structure

The app renders a single `Dashboard` page with five tabs:

| Tab | Contents |
|-----|----------|
| **Overview** | Ticker search, candlestick chart, AI recommendation card, agent radar, stock fundamentals, anomaly panel, opportunity radar, flow chart, signal history chart |
| **Signals** | Stock screener, sector heatmap, market heatmap, insider activity, network graph |
| **Global Intel** | Global markets panel (crypto / FX / sectors), fear & greed gauge, macro signal panel, commodity strip, geo-risk panel |
| **Company** | News articles list, corporate filings, watchlist, report download, recommendation history |
| **Portfolio** | Portfolio manager (holdings, P&L, rebalancing) |

A floating `NLQButton` and `NLQPanel` are always present on top of every tab. A `GlobalMarketBar` scrolling ticker runs below the header.

## Key Components

| Component | Description |
|-----------|-------------|
| `TickerSearch` | Autocomplete search that sets the active ticker in global store |
| `ChartView` | OHLCV candlestick chart powered by lightweight-charts |
| `RecommendationCard` | Shows BUY/HOLD/SELL verdict with confidence, sentiment, and key factors |
| `AgentRadar` | Radar chart of multi-dimensional agent signal scores |
| `StockFundamentals` | P/E, EPS, market cap, and other key fundamental metrics |
| `AnomalyPanel` | Price/volume anomaly detection results |
| `OpportunityRadar` | Top alpha-generating opportunities from the screener |
| `FlowChart` | FII/DII and institutional fund-flow visualisation |
| `HistoryChart` | Sparkline history of the last 10 recommendations |
| `StockScreener` | Filterable table by sector, direction, and alpha threshold |
| `SectorHeatmap` | Colour-coded sector performance grid |
| `MarketHeatmap` | Per-ticker sentiment score heatmap |
| `InsiderActivity` | Recent bulk/block deals and promoter transactions |
| `NetworkGraph` | Correlation network among watched stocks |
| `GlobalMarketsPanel` | Live crypto, FX, and global sector data from WorldMonitor |
| `FearGreedGauge` | CNN-style fear & greed dial |
| `MacroSignalPanel` | FRED-sourced macro indicators (rates, CPI, yield curve) |
| `CommodityStrip` | Live prices for gold, silver, crude oil, natural gas |
| `GeoRiskPanel` | Geopolitical risk scoring affecting Indian markets |
| `ArticlesList` | RAG-retrieved news articles with threat classification |
| `CorporateFilings` | NSE/BSE filing browser for the active ticker |
| `WatchlistPanel` | Persistent watchlist with quick-add |
| `ReportDownload` | Generate and download a full AI research report |
| `PortfolioManager` | Add/remove holdings, view live P&L and allocation |
| `NLQPanel` | Two-stage AI query panel with SSE streaming and dynamic charts |
| `NLQButton` | Floating action button that opens NLQPanel |
| `GlobalMarketBar` | Bloomberg-style scrolling indices/commodities ticker |
| `NotificationBell` | Unread insight count with dropdown |
| `SystemStatus` | Backend health indicator in the header |

## State Management

Global state is managed with Zustand (`src/store/appStore.ts`, persisted to `localStorage` as `alphastream-store`).

Key slices:

| Slice | Type | Purpose |
|-------|------|---------|
| `currentTicker` | `string` | Active stock symbol (default: `RELIANCE`) |
| `recommendation` | `Recommendation \| null` | Latest AI recommendation |
| `recommendationHistory` | `Recommendation[]` | Last 10 recommendations |
| `articles` | `Article[]` | RAG-retrieved news for active ticker |
| `portfolio` | `Holding[]` | User holdings (ticker, quantity, buy price) |
| `watchlist` | `string[]` | Up to 20 watched tickers |
| `globalIndices` | array | WorldMonitor live index quotes |
| `commodityQuotes` | array | WorldMonitor commodity prices |
| `fearGreed` | object | Fear & greed score and label |
| `macroSignals` | object | FRED macro signal summary |
| `nlqOpen` | `boolean` | Whether the NLQ panel is visible |
| `nlqSessionId` | `string` | Conversation session for the NLQ agent |
| `activeTab` | `string` | Currently selected dashboard tab |
| `user` | `UserProfile \| null` | Authenticated user (email, name, role) |

Real-time data arrives via a WebSocket at `/ws/stream/{ticker}` with auto-reconnect (exponential back-off, 5 retries). Message types: `market_update`, `metrics_update`, `agent_update`, `global_market_update`, `recommendation`.

## NLQ Panel

`NLQPanel.jsx` provides a two-stage AI query interface:

- **Stage 1 (compact)**: floating panel above the FAB button; page remains interactive behind it
- **Stage 2 (expanded)**: full-screen centred modal with a dedicated chart area

Queries stream via SSE at `GET /api/nlq/stream`. The response emits agent thought-process steps in real time before delivering the final answer.

Dynamic chart types rendered inline from `chart_spec`:

| Type | Renderer |
|------|----------|
| `line` | SVG area/line chart |
| `bar` | Recharts `BarChart` |
| `scatter` | SVG scatter plot |
| `donut` | SVG donut/pie chart |
| `table` | Compact data table |
| `number` | Single KPI card |

Context-aware prompt suggestions update automatically based on the active dashboard tab (Overview, Signals, Global Intel, Company, Portfolio).

## API Layer

`src/services/api.ts` exports `apiService` — an Axios-backed client with 30+ methods grouped by domain:

- **Core**: `getRecommendation`, `getArticles`, `getHealth`, `ingestArticle`
- **Market**: `getMarketHeatmap`, `getOHLCV`, `getFlows`, `getPatterns`, `getBacktest`, `getPopularTickers`, `getRadar`, `getScreener`, `getTickers`, `getBulkDeals`
- **Portfolio**: `setPortfolio`, `getPortfolioSummary`
- **NLQ**: `nlqQuery`, `openNLQStream`
- **Insights**: `getInsights`, `getInsightsCount`, `markInsightRead`, `dismissInsight`
- **Global (WorldMonitor)**: `getGlobalIndices`, `getCommodityQuotes`, `getCryptoQuotes`, `getVix`, `getFearGreed`, `getSectorPerformance`, `getMacroSignals`, `getCurrencyQuotes`, `getGeoRisk`, `refreshGlobalData`
- **Fundamentals**: `getFundamentals`
- **Filings**: `getFilings`
- **Anomalies**: `getAnomalies`
- **Insider / Reports**: `getInsiderActivity`, `generateReport`
- **News**: `getNews`

The base URL is read from the `VITE_API_URL` environment variable (falls back to `http://localhost:8000`).

## Setup

```bash
cd frontend
npm install
cp .env.example .env  # set VITE_API_URL=http://localhost:8000
npm run dev           # http://localhost:5173
npm run build         # production build (tsc -b && vite build)
```

## Tech Stack

| Library | Version | Role |
|---------|---------|------|
| React | 19 | UI framework |
| TypeScript | 5.9 | Type safety |
| Vite | 7 | Build tool and dev server |
| Tailwind CSS | 4 | Utility-first styling |
| Zustand | 5 | Global state management |
| Recharts | 3 | Bar/composed charts |
| lightweight-charts | 5 | Candlestick OHLCV chart |
| Framer Motion | 12 | Animations (NLQ panel) |
| Axios | 1 | HTTP client |
| React Router | 7 | Client-side routing |
| Radix UI | various | Accessible UI primitives |
