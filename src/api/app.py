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

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import asyncio

from src.agents.sentiment_agent import SentimentAgent
from src.agents.technical_agent import TechnicalAgent
from src.agents.risk_agent import RiskAgent
from src.agents.decision_agent import DecisionAgent
from src.agents.insider_agent import InsiderAgent
from src.agents.chart_agent import ChartAgent
from src.agents.report_agent import ReportAgent
from src.pipeline.rag_core import RAGPipeline

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        # Map ticker -> list of websockets
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, ticker: str):
        await websocket.accept()
        if ticker not in self.active_connections:
            self.active_connections[ticker] = []
        self.active_connections[ticker].append(websocket)
        logger.info(f"Client connected to stream for {ticker}")

    def disconnect(self, websocket: WebSocket, ticker: str):
        if ticker in self.active_connections:
            if websocket in self.active_connections[ticker]:
                self.active_connections[ticker].remove(websocket)
            if not self.active_connections[ticker]:
                del self.active_connections[ticker]
        logger.info(f"Client disconnected from {ticker}")

    async def broadcast(self, ticker: str, message: dict):
        if ticker in self.active_connections:
            for connection in self.active_connections[ticker]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {ticker}: {e}")

    async def broadcast_global(self, message: dict):
        """Broadcast to ALL connected clients."""
        for ticker_conns in self.active_connections.values():
            for connection in ticker_conns:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

class MarketState:
    """Tracks global market sentiment for heatmap."""
    def __init__(self):
        self.sentiments: dict[str, float] = {}  # Ticker -> Score
        self.last_updated: dict[str, str] = {}
        
    def update(self, ticker: str, score: float):
        self.sentiments[ticker] = score
        self.last_updated[ticker] = datetime.utcnow().isoformat()
        
    def get_heatmap(self):
        return [
            {"ticker": t, "score": s, "updated": self.last_updated.get(t)}
            for t, s in self.sentiments.items()
        ]

# Global components - Core agents
rag_pipeline: RAGPipeline | None = None
sentiment_agent: SentimentAgent | None = None
technical_agent: TechnicalAgent | None = None
risk_agent: RiskAgent | None = None
decision_agent: DecisionAgent | None = None

# Global components - SEC agents (Stage 5)
insider_agent: InsiderAgent | None = None
chart_agent: ChartAgent | None = None
report_agent: ReportAgent | None = None

ws_manager = ConnectionManager()
market_state = MarketState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    global rag_pipeline, sentiment_agent, technical_agent, risk_agent, decision_agent
    global insider_agent, chart_agent, report_agent
    
    logger.info("Initializing AlphaStream Live AI...")

    # Initialize core agents
    rag_pipeline = RAGPipeline()
    sentiment_agent = SentimentAgent()
    technical_agent = TechnicalAgent()
    risk_agent = RiskAgent()
    decision_agent = DecisionAgent()
    
    # Initialize SEC agents (Stage 5)
    insider_agent = InsiderAgent()
    chart_agent = ChartAgent()
    report_agent = ReportAgent()

    # Ingest demo data
    demo_articles = get_demo_articles()
    rag_pipeline.ingest_articles(demo_articles)
    
    # Initialize market state with demo data logic (mock)
    market_state.update("AAPL", 0.6)
    market_state.update("MSFT", 0.8) 
    market_state.update("TSLA", -0.4)
    market_state.update("GOOGL", 0.3)
    market_state.update("AMZN", 0.5)
    
    # Capture loop for thread-safe scheduling
    loop = asyncio.get_running_loop()
    
    async def trigger_update(ticker):
        try:
            rec = await generate_recommendation_logic(ticker)
            
            # Update Market State
            market_state.update(ticker, rec.sentiment_score)
            
            # Broadcast Recommendation
            await ws_manager.broadcast(ticker, rec.model_dump())
            
            # Broadcast Heatmap Update
            await ws_manager.broadcast_global({
                "type": "market_update",
                "data": market_state.get_heatmap()
            })
            
        except Exception as e:
            logger.error(f"Failed to update stream for {ticker}: {e}")

    def on_new_article(article):
        """Callback for new articles from Pathway."""
        # Pathway might return a dict or tuple. Ensure dict.
        if not isinstance(article, dict):
            # If tuple, map to schema? Assuming dict for now via python.read
            pass
            
        ingest_start = time.time()
        
        # 1. Ingest
        rag_pipeline.ingest_article(article)
        
        # Calculate Indexing Latency
        indexing_latency = (time.time() - ingest_start) * 1000
        
        # Broadcast Metrics
        asyncio.run_coroutine_threadsafe(
            ws_manager.broadcast_global({
                "type": "metrics_update",
                "data": {
                    "indexing_latency_ms": round(indexing_latency, 2),
                    "total_docs": rag_pipeline.document_count
                }
            }),
            loop
        )

        active_tickers = list(ws_manager.active_connections.keys())
        text = (article.get('title', '') + " " + article.get('content', '')).upper()
        
        for ticker in active_tickers:
            if ticker in text or "MARKET" in text:
                asyncio.run_coroutine_threadsafe(
                    trigger_update(ticker), 
                    loop
                )

    # --- Pathway Integration ---
    from src.connectors.news_connector import create_news_table
    import threading
    import pathway as pw

    # 1. Create the streaming table
    news_table = create_news_table(refresh_interval=60)
    
    # 2. Subscribe to updates
    # Note: subscribe receives (event, new_row, old_row). We only care about new additions.
    def pathway_callback(key, new_row, old_row):
        if new_row:
             # new_row is a dict matching the schema
             on_new_article(new_row)

    # Use pw.io.subscribe to hook the table to our callback
    # If subscribe is not available in some versions, we might need a workaround,
    # but it's the standard way to bridge PW -> Python.
    pw.io.subscribe(news_table, pathway_callback)

    # 3. Run Pathway in a background thread
    logger.info("Starting Pathway engine in background thread...")
    pw_thread = threading.Thread(target=pw.run, daemon=True)
    pw_thread.start()

    logger.info(f"System initialized with {rag_pipeline.document_count} document chunks")

    yield

    logger.info("Shutting down...")
    # pw.run is infinite, daemon thread will be killed on exit



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
    technical_score: float = 0.0 # -1.0 to +1.0
    risk_score: float = 0.0 # 0.0 to 10.0 (or normalized)
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
    """Get trading recommendation."""
    if not rag_pipeline or not sentiment_agent:
        raise HTTPException(status_code=503, detail="System not initialized")

    try:
        return await generate_recommendation_logic(request.ticker.upper())
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def generate_recommendation_logic(ticker: str) -> RecommendationResponse:
    """Core logic to generate a recommendation."""
    start_time = time.time()
    
    # 1. Retrieve
    query = f"{ticker} stock news"
    retrieved_docs = rag_pipeline.retrieve(query, k=5)
    
    if not retrieved_docs:
        # If no docs, we might still want to return Technical/Risk? 
        # For now, let's proceed but sentiment will be neutral.
        logger.warning(f"No docs found for {ticker} during update")
        # Proceed with empty list? Or fail?
        # SentimentAgent handles empty list by returning Neutral.
    
    # 2. Sentiment
    sentiment = sentiment_agent.analyze(retrieved_docs)
    
    # 3. Technical
    technical = technical_agent.analyze(ticker)
    
    # 4. Risk
    risk = risk_agent.analyze(ticker, technical)
    
    # 5. Decision
    final_decision = decision_agent.decide(ticker, sentiment, technical, risk)
    
    latency_ms = (time.time() - start_time) * 1000
    
    combined_factors = [final_decision.get("reasoning", "")]
    combined_factors.extend(sentiment.get("key_factors", [])[:2])
    combined_factors.extend(technical.get("key_signals", [])[:2])
    combined_factors = [f for f in combined_factors if f]

    return RecommendationResponse(
        ticker=ticker,
        timestamp=datetime.utcnow().isoformat(),
        recommendation=final_decision.get("recommendation", "HOLD").upper(),
        confidence=final_decision.get("confidence", 0.0) * 100,
        sentiment_score=sentiment["sentiment_score"],
        sentiment_label=sentiment["sentiment_label"],
        technical_score=technical.get("technical_score", 0.0),
        risk_score=risk.get("risk_score", 0.0),
        key_factors=combined_factors[:5],
        sources=[doc.get("source", "Unknown") for doc in retrieved_docs],
        latency_ms=round(latency_ms, 2),
    )


@app.websocket("/ws/stream/{ticker}")
async def websocket_endpoint(websocket: WebSocket, ticker: str):
    """WebSocket endpoint for real-time updates."""
    ticker = ticker.upper()
    await ws_manager.connect(websocket, ticker)
    try:
        # Send initial recommendation
        if rag_pipeline:
            rec = await generate_recommendation_logic(ticker)
            # Send rec
            await websocket.send_json(rec.model_dump())
            
            # Send initial heatmap
            await websocket.send_json({
                "type": "market_update",
                "data": market_state.get_heatmap()
            })
            
        while True:
            # Keep connection alive, wait for disconnect
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, ticker)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            ws_manager.disconnect(websocket, ticker)
        except:
            pass


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


# ============================================================================
# SEC EDGAR ENDPOINTS (Stage 5)
# ============================================================================

@app.get("/insider/{ticker}")
async def get_insider_activity(ticker: str, days: int = 1) -> dict[str, Any]:
    """
    Get insider trading activity for a ticker.
    
    Fetches Form 4 filings from SEC EDGAR and analyzes patterns.
    Uses LLM to summarize insider sentiment.
    """
    if not insider_agent:
        raise HTTPException(status_code=503, detail="Insider agent not initialized")
    
    ticker = ticker.upper()
    
    try:
        result = insider_agent.analyze(ticker, days=days)
        return {
            "ticker": ticker,
            "period_days": days,
            **result
        }
    except Exception as e:
        logger.error(f"Insider analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chart/{ticker}")
async def get_price_chart(ticker: str, days: int = 7) -> dict[str, Any]:
    """
    Generate a price comparison chart.
    
    Creates a 7-day chart with last 24 hours highlighted.
    Returns chart path and price analysis.
    """
    if not chart_agent:
        raise HTTPException(status_code=503, detail="Chart agent not initialized")
    
    ticker = ticker.upper()
    
    try:
        # Get insider data for overlay
        insider_data = insider_agent.analyze(ticker, days=1) if insider_agent else {}
        insider_events = []  # Extract events if available
        
        result = chart_agent.generate_comparison_chart(
            ticker, 
            insider_events=insider_events,
            days=days
        )
        return result
    except Exception as e:
        logger.error(f"Chart generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/report/{ticker}")
async def generate_full_report(ticker: str) -> dict[str, Any]:
    """
    Generate a comprehensive PDF trading report.
    
    Combines all agent analyses into a professional document:
    - Trading recommendation
    - Price chart
    - Insider trading activity
    - Technical and risk analysis
    """
    if not report_agent:
        raise HTTPException(status_code=503, detail="Report agent not initialized")
    
    ticker = ticker.upper()
    
    try:
        # Gather all data
        recommendation = await generate_recommendation_logic(ticker)
        
        insider_data = insider_agent.analyze(ticker, days=1) if insider_agent else {}
        
        chart_data = chart_agent.generate_comparison_chart(ticker) if chart_agent else {}
        
        technical_data = technical_agent.analyze(ticker) if technical_agent else {}
        
        risk_data = risk_agent.analyze(ticker, technical_data) if risk_agent else {}
        
        # Generate report
        result = report_agent.generate_report(
            ticker=ticker,
            recommendation=recommendation.model_dump(),
            insider_data=insider_data,
            chart_data=chart_data,
            technical_data=technical_data,
            risk_data=risk_data
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Report generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
