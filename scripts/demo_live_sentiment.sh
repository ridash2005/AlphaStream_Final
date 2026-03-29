#!/bin/bash
# ───────────────────────────────────────────────────────────────
# Demo: Live Sentiment Shift
#
# Usage:
#   ./scripts/demo_live_sentiment.sh bearish   # push bearish article
#   ./scripts/demo_live_sentiment.sh bullish   # push bullish article
#
# The dashboard will update automatically within ~10 seconds
# (recommendation card, sentiment score, key factors all change)
# ───────────────────────────────────────────────────────────────

API="${VITE_API_URL:-http://localhost:8000}"
MODE="${1:-bearish}"

if [ "$MODE" = "bearish" ]; then
  echo "📰 Injecting BEARISH breaking news about RELIANCE..."
  curl -s -X POST "$API/ingest" \
    -H "Content-Type: application/json" \
    -d '{
      "title": "BREAKING: Reliance Industries faces major regulatory probe, FII selling accelerates",
      "content": "Reliance Industries Ltd (RELIANCE.NS) shares dropped sharply today as news broke that SEBI has initiated a formal investigation into related-party transactions worth over Rs 15,000 crore. Foreign institutional investors dumped Rs 3,200 crore worth of Reliance shares in the last two sessions, the largest FII exodus from the stock in six months. Analysts at Goldman Sachs downgraded the stock to SELL with a target price cut of 18%, citing governance risks and regulatory overhang. The company'\''s petrochemicals division also reported a 23% decline in margins due to overcapacity in Asian markets. Multiple brokerages have placed the stock under review. Promoter pledge levels have risen to 4.2% from 1.8% last quarter, raising additional concerns about insider confidence.",
      "source": "ET Markets Breaking Alert"
    }' | python3 -m json.tool 2>/dev/null || echo "(response above)"

elif [ "$MODE" = "bullish" ]; then
  echo "📰 Injecting BULLISH breaking news about RELIANCE..."
  curl -s -X POST "$API/ingest" \
    -H "Content-Type: application/json" \
    -d '{
      "title": "BREAKING: Reliance Jio signs massive $4B deal with Google, FII buying surges",
      "content": "Reliance Industries Ltd (RELIANCE.NS) surged 6% in early trade after Jio Platforms announced a transformative $4 billion strategic partnership with Google Cloud for AI infrastructure across India. The deal includes exclusive deployment of Gemini models on Jio'\''s 450 million subscriber base. Foreign institutional investors have been net buyers of Rs 4,800 crore in Reliance over the past five sessions - the strongest FII buying streak since January 2024. Morgan Stanley upgraded the stock to OVERWEIGHT with a revised target price of Rs 3,400, implying 28% upside. Reliance Retail also posted record quarterly revenue of Rs 78,000 crore, beating consensus estimates by 12%. Mukesh Ambani increased promoter stake by 0.3% through open market purchases, signaling strong insider confidence.",
      "source": "ET Markets Breaking Alert"
    }' | python3 -m json.tool 2>/dev/null || echo "(response above)"

else
  echo "Usage: $0 [bearish|bullish]"
  exit 1
fi

echo ""
echo "✅ Article ingested. Watch the dashboard - recommendation will update automatically."
