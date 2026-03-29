# AlphaStream India - Impact Model

## Problem Scale

- **14 Cr+** demat accounts in India (CDSL + NSDL)
- **~3 Cr** active traders
- Average retail investor spends **2+ hours/day** on research
- **80%** rely on WhatsApp tips and unverified sources
- Average missed opportunity cost: **₹3,000-10,000/quarter**

## Market Opportunity (TAM / SAM / SOM)

| Level | Segment | Size | Notes |
|---|---|---|---|
| **TAM** | Total Indian equity market participants | 14 Cr | CDSL + NSDL demat accounts (2024) |
| **SAM** | Active traders who research daily | ~3 Cr | ~20% of demat accounts trade monthly |
| **SOM** | Realistic 5-year premium capture (0.5%) | 1.5 L | Conservative; industry freemium converts at 0.5-1% |

> **Key assumption**: SOM uses 0.5% of SAM, not TAM — anchored to paying users, not total accounts.

## AlphaStream India Impact

### 1. Time Saved

| Metric | Without AlphaStream | With AlphaStream |
|---|---|---|
| Daily research time | 2+ hours | 15 minutes |
| Filing analysis | Manual reading (30 min/filing) | Instant LLM classification |
| Insider trade monitoring | Manual NSE checks | Automated alerts |
| FII/DII tracking | Visit NSDL website daily | Real-time flow analysis |

**Time saved**: 1.75 hrs/day × ₹500/hr × 250 trading days = **₹2.19L/user/year**

### 2. Alpha Generated

| Signal Type | Detection | Backtest Win Rate | Avg Return (30d) |
|---|---|---|---|
| RSI Divergence | Automated scan across Nifty 500 | 60-78% | +3.26% |
| MACD Crossover | Real-time detection | 45-57% | +0.71% |
| Insider Cluster Buying | 3+ insiders in 30 days | Historical strong signal | Varies |
| FII Buying Streak | 5+ consecutive sessions | ~72% (historical) | +3-5% |

**Conservative estimate**: 2-3 actionable signals/month × 60% accuracy × ₹3,000 avg = **₹54,000/user/year**

### 3. Risk Reduction

- Early warning on adverse signals prevents panic selling
- Portfolio-aware alerts: "Your IT holdings at risk from FII selling"
- Backtested confidence: "This pattern has worked 78% of the time on this stock"
- Estimated **15% reduction** in behavioral losses

### 4. ET Markets Business Impact

| Metric | Estimate | Assumption |
|---|---|---|
| **Increased engagement** | +40% time on platform | Signal-dependent users return daily |
| **Premium conversion** | 0.3% free → paid | ₹999/month subscription |
| **Revenue (Year 1)** | ₹59.9 Cr/year | 50K early-adopter premium users × ₹999 × 12 |
| **Reduced churn** | 2x retention | Signal-dependent users have higher stickiness |

#### Revenue Projection (ET Markets Premium)

| | Year 1 | Year 3 | Year 5 |
|---|---|---|---|
| Premium users | 50,000 | 2,00,000 | 5,00,000 |
| Price (₹/month) | ₹999 | ₹999 | ₹999 |
| **Annual Revenue** | **₹59.9 Cr** | **₹239.8 Cr** | **₹599.4 Cr** |

> **Assumptions**: Year 1 = early-adopter base from existing ET Markets free users. Year 3 = viral growth via portfolio alerts sharing. Year 5 = network effects + Tier 2/3 city expansion.

#### Cost Reduction for ET Markets

| Cost Category | Current Approach | With AlphaStream | Estimated Saving |
|---|---|---|---|
| Signal content (est. ₹20 Cr/year) | Manual analyst teams + editorial curation | LLM-generated, human-reviewed signal summaries | **₹5-10 Cr/year (30%)** |

> Automated signal pipelines handle high-frequency, repeatable content (FII flows, insider alerts, technical scans). Humans focus on narrative, investigative, and opinion content — higher value, lower volume.

## Competitive Moat

- **India-specific regulatory data**: Direct integration with NSE SAST/PIT filings and NSDL FII/DII data — not available via generic global APIs.
- **Backtested signals, not LLM speculation**: Every signal carries a win rate grounded in historical NSE/BSE data; pure LLM wrappers cannot provide this without the same data pipeline.
- **Real-time streaming architecture**: Pathway-powered incremental ingestion with sub-second updates; static dashboards require full re-computation on each load.
- **Portfolio-aware alerts**: Signals are contextualised to a user's actual holdings — generic screeners give the same alert to everyone regardless of exposure.
- **Compound moat over time**: Each user interaction (query, alert acknowledgment) improves signal ranking; the system gets more accurate as the user base grows.

## Assumptions (Stated Explicitly)

1. Win rates based on backtesting against Nifty 50 stocks with 3-5 year data
2. Average return estimates use median, not mean (to reduce outlier effect)
3. Time savings assumes basic digital literacy and daily market participation
4. Premium conversion rate of 0.3% is conservative (industry average 0.5-1%)
5. Back-of-envelope calculations — detailed validation would require A/B testing
6. SOM (1.5L users) = 0.5% of SAM (3 Cr active traders) — conservative for a 5-year horizon
7. Revenue projections assume no price increase over 5 years (understates upside)
8. Cost reduction estimate (₹5-10 Cr/year) assumes research content budget of ~₹20 Cr/year for a platform at ET Markets' scale
9. Year 3 and Year 5 user projections assume compounding growth of ~100% and ~150% respectively from Year 1 base

## What Makes This Different

| What 99% of teams build | What AlphaStream builds |
|---|---|
| Call GPT-4 → get text blob | Text2SQL pipeline → grounded in real data |
| No verification | Historical backtest with win rates |
| Mock data | Live NSE/BSE/FII data |
| Streamlit dashboard | Production React + WebSocket |
| No guardrails | Input/output guardrails + correction loop |
| Single ticker lookup | Multi-signal fusion (Alpha Score) |
