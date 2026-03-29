# AlphaStream India - Impact Model

## Problem Scale

- **14 Cr+** demat accounts in India (CDSL + NSDL)
- **~3 Cr** active traders
- Average retail investor spends **2+ hours/day** on research
- **80%** rely on WhatsApp tips and unverified sources
- Average missed opportunity cost: **₹3,000-10,000/quarter**

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
| **Revenue** | ₹53.7 Cr/year | 3 Cr users × 0.3% × ₹999 × 12 |
| **Reduced churn** | 2x retention | Signal-dependent users have higher stickiness |

## Assumptions (Stated Explicitly)

1. Win rates based on backtesting against Nifty 50 stocks with 3-5 year data
2. Average return estimates use median, not mean (to reduce outlier effect)
3. Time savings assumes basic digital literacy and daily market participation
4. Premium conversion rate of 0.3% is conservative (industry average 0.5-1%)
5. Back-of-envelope calculations - detailed validation would require A/B testing

## What Makes This Different

| What 99% of teams build | What AlphaStream builds |
|---|---|
| Call GPT-4 → get text blob | Text2SQL pipeline → grounded in real data |
| No verification | Historical backtest with win rates |
| Mock data | Live NSE/BSE/FII data |
| Streamlit dashboard | Production React + WebSocket |
| No guardrails | Input/output guardrails + correction loop |
| Single ticker lookup | Multi-signal fusion (Alpha Score) |
