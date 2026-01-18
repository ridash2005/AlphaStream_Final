"""
FastAPI application for AlphaStream Live AI.

Provides REST API endpoints for trading recommendations.
"""

import os
# Force CPU usage to avoid CUDA driver issues
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.agents.sentiment_agent import SentimentAgent
from src.agents.technical_agent import TechnicalAgent
from src.agents.risk_agent import RiskAgent
from src.agents.decision_agent import DecisionAgent
from src.pipeline.rag_core import RAGPipeline

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


# Global components
rag_pipeline: RAGPipeline | None = None
sentiment_agent: SentimentAgent | None = None
technical_agent: TechnicalAgent | None = None
risk_agent: RiskAgent | None = None
decision_agent: DecisionAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    global rag_pipeline, sentiment_agent, technical_agent, risk_agent, decision_agent, orchestrator
    
    logger.info("Initializing AlphaStream Live AI...")

    # Initialize components
    rag_pipeline = RAGPipeline()
    sentiment_agent = SentimentAgent()
    technical_agent = TechnicalAgent()
    risk_agent = RiskAgent()
    decision_agent = DecisionAgent()

    # Ingest demo data
    demo_articles = get_demo_articles()
    rag_pipeline.ingest_articles(demo_articles)
    
    # Start Live News Polling
    from src.connectors.polling import NewsPoller
    news_poller = NewsPoller(callback=rag_pipeline.ingest_article, interval=60)
    news_poller.start()

    logger.info(f"System initialized with {rag_pipeline.document_count} document chunks")

    yield

    logger.info("Shutting down...")
    news_poller.stop()


app = FastAPI(
    title="AlphaStream Live AI",
    description="Real-time trading recommendations powered by Pathway streaming RAG",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class RecommendationRequest(BaseModel):
    """Request model for trading recommendation."""

    ticker: str = Field(..., description="Stock ticker symbol (e.g., AAPL)")
    query: str | None = Field(None, description="Optional custom query")


class RecommendationResponse(BaseModel):
    """Response model for trading recommendation."""

    ticker: str
    timestamp: str
    recommendation: str  # BUY, HOLD, SELL
    confidence: float  # 0-100
    sentiment_score: float  # -1.0 to +1.0
    sentiment_label: str  # BEARISH, NEUTRAL, BULLISH
    key_factors: list[str]
    sources: list[str]
    latency_ms: float


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: str
    document_count: int
    components: dict[str, bool]


# Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """System health check."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        document_count=rag_pipeline.document_count if rag_pipeline else 0,
        components={
            "rag_pipeline": rag_pipeline is not None,
            "sentiment_agent": sentiment_agent is not None,
            "technical_agent": technical_agent is not None,
            "risk_agent": risk_agent is not None,
            "decision_agent": decision_agent is not None,
        },
    )


@app.post("/recommend", response_model=RecommendationResponse)
async def get_recommendation(request: RecommendationRequest) -> RecommendationResponse:
    """
    Get trading recommendation for a ticker.

    This endpoint:
    1. Retrieves relevant news articles about the ticker
    2. Analyzes sentiment using LLM
    3. Returns recommendation with confidence score
    """
    start_time = time.time()

    if not rag_pipeline or not sentiment_agent:
        raise HTTPException(status_code=503, detail="System not initialized")

    ticker = request.ticker.upper()

    try:
        # Build query
        query = f"{ticker} stock news"
        if request.query:
            query = f"{ticker} {request.query}"

        # Retrieve relevant documents
        retrieved_docs = rag_pipeline.retrieve(query, k=5)

        if not retrieved_docs:
            raise HTTPException(status_code=404, detail=f"No articles found for {ticker}")

        # 1. Sentiment Analysis
        sentiment = sentiment_agent.analyze(retrieved_docs)

        # 2. Technical Analysis
        technical = technical_agent.analyze(ticker)
        
        # 3. Risk Assessment
        risk = risk_agent.analyze(ticker, technical)
        
        # 4. Final Decision
        final_decision = decision_agent.decide(
            ticker, 
            sentiment, 
            technical, 
            risk
        )

        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        
        # Format key factors (combine reasoning + specific factors)
        combined_factors = [final_decision.get("reasoning", "")]
        combined_factors.extend(sentiment.get("key_factors", [])[:2])
        combined_factors.extend(technical.get("key_signals", [])[:2])
        combined_factors = [f for f in combined_factors if f] # Filter empty

        return RecommendationResponse(
            ticker=ticker,
            timestamp=datetime.utcnow().isoformat(),
            recommendation=final_decision.get("recommendation", "HOLD").upper(),
            confidence=final_decision.get("confidence", 0.0) * 100,
            sentiment_score=sentiment["sentiment_score"],
            sentiment_label=sentiment["sentiment_label"],
            key_factors=combined_factors[:5], # Limit to 5
            sources=[doc.get("source", "Unknown") for doc in retrieved_docs],
            latency_ms=round(latency_ms, 2),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/articles/{ticker}")
async def get_ticker_articles(ticker: str, limit: int = 10) -> dict[str, Any]:
    """Get latest articles for a ticker."""
    if not rag_pipeline:
        raise HTTPException(status_code=503, detail="System not initialized")

    ticker = ticker.upper()
    query = f"{ticker} stock news"

    articles = rag_pipeline.retrieve(query, k=limit)

    return {
        "ticker": ticker,
        "count": len(articles),
        "articles": [
            {
                "title": a.get("title", "Unknown"),
                "source": a.get("source", "Unknown"),
                "similarity": round(a.get("similarity", 0), 4),
                "snippet": a.get("text", "")[:200] + "...",
            }
            for a in articles
        ],
    }


@app.post("/ingest")
async def ingest_article(article: dict[str, Any]) -> dict[str, Any]:
    """
    Ingest a new article into the system.
    
    Useful for testing real-time updates.
    """
    if not rag_pipeline:
        raise HTTPException(status_code=503, detail="System not initialized")

    required_fields = ["title", "content"]
    for field in required_fields:
        if field not in article:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    # Add defaults
    article.setdefault("id", f"manual_{time.time()}")
    article.setdefault("source", "Manual")
    article.setdefault("url", "")
    article.setdefault("published_at", datetime.utcnow().isoformat())

    chunks_created = rag_pipeline.ingest_article(article)

    return {
        "status": "success",
        "chunks_created": chunks_created,
        "document_count": rag_pipeline.document_count,
    }


# Helper functions
def score_to_recommendation(score: float) -> str:
    """Convert sentiment score to recommendation."""
    if score > 0.3:
        return "BUY"
    elif score < -0.3:
        return "SELL"
    return "HOLD"


def get_demo_articles() -> list[dict[str, Any]]:
    """Get demo articles for testing."""
    return [
        {
            "id": "demo1",
            "title": "Apple Reports Record Q4 Earnings",
            "content": "Apple Inc. reported record quarterly earnings, beating analyst expectations with strong iPhone 15 sales. Revenue increased 8% year-over-year to $95 billion. CEO Tim Cook highlighted growth in Services and emerging markets.",
            "source": "Reuters",
            "url": "https://example.com/apple-earnings",
            "published_at": datetime.utcnow().isoformat(),
        },
        {
            "id": "demo2",
            "title": "Microsoft Cloud Revenue Surges 30%",
            "content": "Microsoft Azure saw 30% year-over-year growth in Q4, exceeding Wall Street expectations. The company's AI investments are paying off with increased enterprise adoption. Cloud computing remains the key growth driver.",
            "source": "CNBC",
            "url": "https://example.com/msft-cloud",
            "published_at": datetime.utcnow().isoformat(),
        },
        {
            "id": "demo3",
            "title": "Tesla Stock Drops on Delivery Miss",
            "content": "Tesla shares fell 5% after the company reported vehicle deliveries below analyst expectations. The EV maker cited production challenges and increased competition. Margins remain under pressure.",
            "source": "Bloomberg",
            "url": "https://example.com/tsla-drop",
            "published_at": datetime.utcnow().isoformat(),
        },
        {
            "id": "demo4",
            "title": "Google AI Breakthrough Boosts Alphabet Stock",
            "content": "Alphabet shares jumped 4% following announcements of major AI breakthroughs in Search and Cloud. The company's Gemini model shows significant improvements over competitors. Ad revenue growth accelerated.",
            "source": "WSJ",
            "url": "https://example.com/googl-ai",
            "published_at": datetime.utcnow().isoformat(),
        },
        {
            "id": "demo5",
            "title": "Amazon Prime Day Sets New Sales Record",
            "content": "Amazon's annual Prime Day event generated record sales, up 12% from last year. AWS continued strong growth while retail margins improved. The company raised full-year guidance.",
            "source": "MarketWatch",
            "url": "https://example.com/amzn-prime",
            "published_at": datetime.utcnow().isoformat(),
        },
    ]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
