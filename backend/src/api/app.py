"""
FastAPI application for AlphaStream Live AI.

Provides REST API endpoints for trading recommendations.
"""

import os
# Force CPU usage to avoid CUDA driver issues
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import asyncio
import json
import logging
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, List, Optional, Callable, Awaitable

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.agents.sentiment_agent import SentimentAgent
from src.agents.technical_agent import TechnicalAgent
from src.agents.risk_agent import RiskAgent
from src.agents.decision_agent import DecisionAgent
from src.agents.insider_agent import InsiderAgent
from src.agents.chart_agent import ChartAgent
from src.agents.report_agent import ReportAgent
from src.agents.flow_agent import FlowAgent
from src.pipeline.rag_core import RAGPipeline
from src.pipeline.rag_service import UnifiedRAGService

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

# Global components - Flow agent (institutional signals)
flow_agent: FlowAgent | None = None

# Global components - SEC agents (Stage 5)
insider_agent: InsiderAgent | None = None
chart_agent: ChartAgent | None = None
report_agent: ReportAgent | None = None

# Unified RAG Service (Adaptive RAG primary, manual fallback)
unified_rag: UnifiedRAGService | None = None

# Track last article ingestion time - for forcing manual RAG on fresh content
last_ingestion_time: float = 0.0

ws_manager = ConnectionManager()
market_state = MarketState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    global rag_pipeline, sentiment_agent, technical_agent, risk_agent, decision_agent
    global flow_agent, insider_agent, chart_agent, report_agent, unified_rag
    
    logger.info("Initializing AlphaStream Live AI...")

    # Initialize core agents
    rag_pipeline = RAGPipeline()
    sentiment_agent = SentimentAgent()
    technical_agent = TechnicalAgent()
    risk_agent = RiskAgent()
    decision_agent = DecisionAgent()
    
    # Initialize flow agent (FII/DII institutional signals)
    flow_agent = FlowAgent()

    # Initialize SEC agents (Stage 5)
    insider_agent = InsiderAgent()
    chart_agent = ChartAgent()
    report_agent = ReportAgent()

    # Seed initial articles for RAG index (these will be replaced by live news)
    # NOTE: Demo articles provide initial context before live news arrives
    # They will be superseded by real-time NewsAPI data via Pathway
    initial_articles = get_demo_articles()
    rag_pipeline.ingest_articles(initial_articles)
    logger.info("Seeded RAG with initial articles. Live news will supersede these.")
    
    # Start Pathway Adaptive RAG Server (USP) as a subprocess
    logger.info("Starting Pathway Adaptive RAG Server (port 8001)...")
    rag_server_process = None
    try:
        # Launch server in background
        rag_server_process = subprocess.Popen(
            [sys.executable, "src/pipeline/adaptive_rag_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd="."  # Run from backend root
        )
        logger.info(f"Adaptive RAG Server started with PID: {rag_server_process.pid}")
        
        # Wait for Adaptive RAG server to be ready
        import httpx
        adaptive_rag_url = os.environ.get("ADAPTIVE_RAG_URL", "http://localhost:8001")
        max_wait = int(os.environ.get("RAG_STARTUP_TIMEOUT", "45"))
        wait_interval = 2
        for i in range(max_wait // wait_interval):
            try:
                with httpx.Client(timeout=3.0) as client:
                    resp = client.get(f"{adaptive_rag_url}/")
                    if resp.status_code in [200, 404, 405]:  # Server is responding
                        logger.info(f"✅ Adaptive RAG Server ready after {(i+1) * wait_interval}s")
                        break
            except Exception:
                pass
            time.sleep(wait_interval)
            logger.info(f"⏳ Waiting for Adaptive RAG Server... ({(i+1) * wait_interval}s)")
        else:
            logger.warning("⚠️ Adaptive RAG Server may not be fully ready, continuing anyway")
    except Exception as e:
        logger.error(f"Failed to start Adaptive RAG Server: {e}")

    # Initialize Unified RAG Service (Adaptive RAG primary, manual fallback)
    unified_rag = UnifiedRAGService(
        adaptive_rag_url=os.environ.get("ADAPTIVE_RAG_URL", "http://localhost:8001"),
        manual_rag=rag_pipeline
    )
    logger.info("Unified RAG Service initialized (Adaptive RAG primary, manual fallback)")
    
    # Initialize DuckDB + seed insights
    try:
        from src.data.market_schema import init_database
        db_result = init_database(load_prices=False)  # Prices already loaded
        logger.info(f"DuckDB ready: {db_result}")
    except Exception as e:
        logger.warning(f"DuckDB init: {e}")

    try:
        from src.api.insights import seed_initial_insights, start_background_insights
        seed_initial_insights()
        start_background_insights(interval_minutes=30)
        logger.info("Ambient insights engine started (every 30 min)")

        # Seed RSS articles into DuckDB for NLQ
        from src.data.article_ingest import ingest_rss_to_duckdb
        rss_count = ingest_rss_to_duckdb()
        logger.info(f"Seeded {rss_count} RSS articles into DuckDB")
    except Exception as e:
        logger.warning(f"Insights engine: {e}")

    # Start data refresh service (replaces sample data with real signals)
    try:
        from src.data.data_refresh import start_background_refresh
        start_background_refresh(interval_minutes=30)
        logger.info("Data refresh scheduler started (every 30 min)")
    except Exception as e:
        logger.warning(f"Data refresh scheduler: {e}")

    # Bootstrap global market data (WorldMonitor integration)
    try:
        from src.connectors.global_market_connector import get_global_market_connector
        gmc = get_global_market_connector()
        gmc.bootstrap()
        logger.info("Global market connector bootstrapped (WorldMonitor integration)")
    except Exception as e:
        logger.warning(f"Global market bootstrap: {e}")

    # Start background refresh for global market data
    async def _global_market_refresh_loop():
        while True:
            from src.config import get_settings
            _settings = get_settings()
            await asyncio.sleep(_settings.global_market_refresh_minutes * 60)
            try:
                from src.connectors.global_market_connector import get_global_market_connector
                gmc = get_global_market_connector()
                gmc.bootstrap()
                # Broadcast updated global data to all WS clients
                await ws_manager.broadcast_global({
                    "type": "global_market_update",
                    "data": {
                        "indices": gmc.get_global_indices(),
                        "commodities": gmc.get_commodity_quotes(),
                        "vix": gmc.get_vix(),
                        "fear_greed": gmc.get_fear_greed(),
                        "crypto": gmc.get_crypto_quotes(),
                        "currencies": gmc.get_currency_quotes(),
                    }
                })
                logger.debug("Global market data refreshed and broadcast")
            except Exception as e:
                logger.warning(f"Global market refresh loop: {e}")

    asyncio.get_running_loop().create_task(_global_market_refresh_loop())
    logger.info("Global market refresh loop started")

    # Market state will be populated dynamically as recommendations are generated

    # Capture loop for thread-safe scheduling
    loop = asyncio.get_running_loop()
    
    async def trigger_update(ticker):
        try:
            rec = await generate_recommendation_logic(ticker)
            
            # Update Market State
            market_state.update(ticker, rec.sentiment_score)
            
            # Broadcast Recommendation
            await ws_manager.broadcast(ticker, {"type": "recommendation", "data": rec.model_dump()})
            
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

        # 0.5 Classify article threat level (WorldMonitor classifier)
        try:
            from src.connectors.news_classifier import classify_article
            from src.connectors.geopolitical_connector import get_geopolitical_connector
            classification = classify_article(
                article.get("title", ""),
                article.get("content", article.get("text", "")),
            )
            article["threat_level"] = classification["level"]
            article["threat_category"] = classification["category"]
            article["threat_confidence"] = classification["confidence"]
            # Feed into geopolitical risk model
            geo = get_geopolitical_connector()
            geo.ingest_classification(classification, article.get("title", ""))
        except Exception as e:
            logger.debug(f"News classification failed: {e}")

        # 1. Ingest into manual RAG
        rag_pipeline.ingest_article(article)

        # 1.5 Also write to DuckDB for NLQ querying
        try:
            from src.data.article_ingest import ingest_article_to_duckdb
            ingest_article_to_duckdb(article)
        except Exception as e:
            logger.warning(f"DuckDB article ingest failed: {e}")
        
        # 2. Also write to data/articles/ for Adaptive RAG to pick up
        try:
            import os
            import hashlib
            articles_dir = "data/articles"
            os.makedirs(articles_dir, exist_ok=True)
            
            # Create unique filename from title hash
            title = article.get('title', 'untitled')
            content = article.get('content', article.get('text', ''))
            source = article.get('source', 'Unknown')
            
            # Generate filename from title hash
            title_hash = hashlib.md5(title.encode()).hexdigest()[:8]
            filename = f"{articles_dir}/article_{title_hash}.txt"
            
            # Write article as simple text format
            with open(filename, 'w') as f:
                f.write(f"Title: {title}\n")
                f.write(f"Source: {source}\n")
                f.write(f"Date: {article.get('published_at', 'Unknown')}\n")
                f.write(f"---\n")
                f.write(content)
            
            logger.debug(f"📝 Wrote article to {filename}")
        except Exception as e:
            logger.warning(f"Failed to write article to disk: {e}")
        
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
    # Note: subscribe receives (key, row, time, is_addition). We only care about new additions.
    def pathway_callback(key, row, time, is_addition):
        if row and is_addition:
             # row is a dict matching the schema
             on_new_article(row)

    # Use pw.io.subscribe to hook the table to our callback
    pw.io.subscribe(news_table, pathway_callback)

    # 3. Run Pathway in a background thread
    def _run_pathway():
        try:
            pw.run()
        except Exception as e:
            logger.error(f"Pathway engine crashed: {e}", exc_info=True)

    logger.info("Starting Pathway engine in background thread...")
    pw_thread = threading.Thread(target=_run_pathway, daemon=True)
    pw_thread.start()

    logger.info(f"System initialized with {rag_pipeline.document_count} document chunks")

    yield
    
    # Graceful shutdown
    logger.info("Shutting down AlphaStream...")
    
    # Terminate Adaptive RAG server if running
    if 'rag_server_process' in locals() and rag_server_process:
        logger.info(f"Terminating Adaptive RAG Server (PID: {rag_server_process.pid})...")
        rag_server_process.terminate()
        try:
            rag_server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("Adaptive RAG Server did not terminate gracefully, killing...")
            rag_server_process.kill()
            
    logger.info("Shutdown complete.")
    # pw.run is infinite, daemon thread will be killed on exit



app = FastAPI(
    title="AlphaStream India",
    description="AI-powered investment intelligence for the Indian investor — signals, NLQ, backtesting",
    version="2.0.0",
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

# Mount NLQ + Market + Insights routers
from src.api.routers.nlq import router as nlq_router
from src.api.routers.market import router as market_router
from src.api.routers.insights import router as insights_router
from src.api.routers.global_market import router as global_market_router

app.include_router(nlq_router, prefix="/api", tags=["NLQ"])
app.include_router(market_router, prefix="/api", tags=["Market"])
app.include_router(insights_router, prefix="/api", tags=["Insights"])
app.include_router(global_market_router, prefix="/api/global", tags=["Global Market"])


# Request/Response models
class RecommendationRequest(BaseModel):
    """Request model for trading recommendation."""

    ticker: str = Field(..., description="Stock ticker symbol (e.g., RELIANCE)")
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
    rag_engine: str = "manual"  # "adaptive" or "manual"
    # Global market context (WorldMonitor enrichment)
    global_verdict: str = ""  # RISK-ON, RISK-OFF, MIXED
    vix: float | None = None
    fear_greed_score: float | None = None


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


@app.get("/market/heatmap")
async def get_market_heatmap() -> dict[str, Any]:
    """Get current market sentiment heatmap data."""
    return {
        "data": market_state.get_heatmap()
    }


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


async def generate_recommendation_logic(ticker: str, update_callback: Callable[[str, str], Awaitable[None]] = None) -> RecommendationResponse:
    """Core logic to generate a recommendation."""
    start_time = time.time()
    
    # helper for updates
    async def send_update(agent: str, status: str):
        if update_callback:
            await update_callback(agent, status)

    # 1. Retrieve using Unified RAG (Adaptive primary, manual fallback)
    await send_update("RAG System", "Retrieving and analyzing market data...")
    query = f"{ticker} stock news financial analysis market sentiment"
    
    # Check if there was a recent ingestion (within 30 seconds)
    # If so, force manual RAG to ensure fresh content is included
    force_manual = (time.time() - last_ingestion_time) < 30.0
    
    if force_manual:
        logger.info("📰 Recent article ingested - using manual RAG for fresh content")
        # Directly use manual RAG for immediate updates
        retrieved_docs = rag_pipeline.retrieve(query, k=5)
        rag_engine = "manual"
        rag_response_answer = rag_pipeline.format_context(retrieved_docs)
        rag_sources = list(set(doc.get("source", "Unknown") for doc in retrieved_docs))
    else:
        # Use unified RAG service (tries Adaptive RAG first, falls back to manual)
        rag_response = unified_rag.query(query, ticker=ticker)
        rag_engine = rag_response.engine  # "adaptive" or "manual"
        rag_response_answer = rag_response.answer
        rag_sources = rag_response.sources if rag_response.sources else []
    
    logger.info(f"🔍 RAG Engine: {rag_engine}")
    
    # For sentiment analysis, we still need document list format
    # If using adaptive RAG, we get processed answer; for manual, we already have docs
    if rag_engine == "manual" and not force_manual:
        # Fallback manual RAG returns raw documents - retrieve them
        retrieved_docs = rag_pipeline.retrieve(query, k=5)
        rag_sources = list(set(doc.get("source", "Unknown") for doc in retrieved_docs))
    elif rag_engine == "adaptive":
        # Adaptive RAG already processed - create synthetic doc list
        retrieved_docs = [{
            "text": rag_response_answer,
            "source": "Pathway Adaptive RAG",
            "title": f"{ticker} Analysis"
        }]
    # else: force_manual already set retrieved_docs above
    
    if not retrieved_docs:
        logger.warning(f"No docs found for {ticker} during update")
    
    logger.info(f"📄 Retrieved {len(retrieved_docs)} docs for sentiment analysis")
    
    await send_update("Sentiment Agent", f"Analyzing {len(retrieved_docs)} documents...")
    # 2. Sentiment
    sentiment = sentiment_agent.analyze(retrieved_docs)
    
    # 3. Technical
    await send_update("Technical Agent", "Calculating RSI, MACD, and trends...")
    technical = technical_agent.analyze(ticker)
    
    # 4. Risk
    await send_update("Risk Agent", "Assessing volatility and position checks...")
    risk = risk_agent.analyze(ticker, technical)

    # 4.5 Flow analysis (FII/DII institutional signals)
    flow_data = {}
    if flow_agent:
        try:
            await send_update("Flow Agent", "Analyzing FII/DII institutional flows...")
            flow_data = flow_agent.analyze(days=30)
        except Exception as e:
            logger.warning(f"Flow agent failed: {e}")

    # 4.6 Global market context (WorldMonitor enrichment)
    global_ctx = {}
    try:
        from src.connectors.global_market_connector import get_global_market_connector
        gmc = get_global_market_connector()
        await send_update("Global Context", "Fetching VIX, Fear & Greed, commodities...")
        global_ctx = gmc.get_decision_context()
    except Exception as e:
        logger.warning(f"Global context fetch failed: {e}")

    # Merge flow data into global context so decision agent sees everything
    if flow_data.get("observations"):
        global_ctx["fii_dii_observations"] = flow_data["observations"][:3]
    if flow_data.get("net_fii"):
        global_ctx["fii_net_flow"] = flow_data["net_fii"]
    if flow_data.get("net_dii"):
        global_ctx["dii_net_flow"] = flow_data["net_dii"]

    # 4.7 Geopolitical risk context
    try:
        from src.connectors.geopolitical_connector import get_geopolitical_connector
        geo = get_geopolitical_connector()
        geo_risk = geo.get_india_risk()
        global_ctx["india_geo_risk"] = geo_risk.get("score", 20)
        global_ctx["india_geo_level"] = geo_risk.get("level", "MODERATE")
        if geo_risk.get("hotspot_alerts"):
            global_ctx["geo_hotspots"] = [h["name"] for h in geo_risk["hotspot_alerts"]]
    except Exception as e:
        logger.debug(f"Geo risk fetch failed: {e}")

    # 5. Decision (now includes flow signals + global context)
    await send_update("Decision Agent", "Synthesizing final recommendation...")
    final_decision = decision_agent.decide(ticker, sentiment, technical, risk, global_ctx)

    latency_ms = (time.time() - start_time) * 1000

    combined_factors = [final_decision.get("reasoning", "")]
    combined_factors.extend(sentiment.get("key_factors", [])[:2])
    combined_factors.extend(technical.get("key_signals", [])[:2])
    # Include flow observations in key factors
    if flow_data.get("observations"):
        combined_factors.extend(flow_data["observations"][:1])
    # Include global market summary
    if global_ctx.get("summary"):
        combined_factors.append(global_ctx["summary"])
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
        sources=rag_sources if rag_sources else [doc.get("source", "Unknown") for doc in retrieved_docs],
        latency_ms=round(latency_ms, 2),
        rag_engine=rag_engine,
        global_verdict=global_ctx.get("global_verdict", ""),
        vix=global_ctx.get("vix"),
        fear_greed_score=global_ctx.get("fear_greed_score"),
    )


@app.websocket("/ws/stream/{ticker}")
async def websocket_endpoint(websocket: WebSocket, ticker: str):
    """WebSocket endpoint for real-time updates."""
    ticker = ticker.upper()
    await ws_manager.connect(websocket, ticker)
    try:
        # Define callback for partial updates
        async def stream_progress(agent: str, status: str):
            await websocket.send_json({
                "type": "agent_update",
                "data": {
                    "agent": agent,
                    "status": status,
                    "timestamp": datetime.utcnow().isoformat()
                }
            })

        # Send initial recommendation with streaming updates
        if rag_pipeline:
            rec = await generate_recommendation_logic(ticker, update_callback=stream_progress)
            
            # Update market state with this ticker's sentiment
            market_state.update(ticker, rec.sentiment_score)
            
            # Send recommendation to this client
            await websocket.send_json({"type": "recommendation", "data": rec.model_dump()})
            
            # Send heatmap to this client
            await websocket.send_json({
                "type": "market_update",
                "data": market_state.get_heatmap()
            })
            
            # Also broadcast heatmap update to ALL connected clients
            await ws_manager.broadcast_global({
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
        except Exception as disconnect_err:
            logger.warning(f"Error during WebSocket disconnect cleanup: {disconnect_err}")


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
    Ingested articles are immediately available in manual RAG
    and will be picked up by Adaptive RAG on next file scan.
    """
    global last_ingestion_time
    
    if not rag_pipeline:
        raise HTTPException(status_code=503, detail="System not initialized")

    required_fields = ["title", "content"]
    for field in required_fields:
        if field not in article:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    # Add defaults
    import uuid
    article.setdefault("id", f"manual_{uuid.uuid4().hex[:12]}")
    article.setdefault("source", "Breaking News")  # Mark as breaking news
    article.setdefault("url", "")
    article.setdefault("published_at", datetime.utcnow().isoformat())

    # Run blocking ingestion in thread pool to avoid blocking the event loop
    loop = asyncio.get_running_loop()
    chunks_created = await loop.run_in_executor(
        None, 
        lambda: rag_pipeline.ingest_article(article)
    )
    
    # Also write to data/articles for Adaptive RAG to pick up
    try:
        import hashlib
        articles_dir = "data/articles"
        os.makedirs(articles_dir, exist_ok=True)
        
        title = article.get('title', 'untitled')
        content = article.get('content', '')
        source = article.get('source', 'Unknown')
        
        title_hash = hashlib.md5(title.encode()).hexdigest()[:8]
        filename = f"{articles_dir}/article_{title_hash}.txt"
        
        with open(filename, 'w') as f:
            f.write(f"Title: {title}\n")
            f.write(f"Source: {source}\n")
            f.write(f"Date: {article.get('published_at', 'Unknown')}\n")
            f.write(f"---\n")
            f.write(content)
        
        logger.info(f"📝 Wrote article to {filename} for Adaptive RAG")
    except Exception as e:
        logger.warning(f"Failed to write article to disk: {e}")
    
    # Track last ingestion time - forces manual RAG for 30 seconds
    last_ingestion_time = time.time()
    
    return {
        "status": "success",
        "chunks_created": chunks_created,
        "document_count": rag_pipeline.document_count,
        "note": "Article immediately available in manual RAG"
    }


# ============================================================================
# SEC EDGAR ENDPOINTS (Stage 5)
# ============================================================================

@app.get("/insider/{ticker}")
async def get_insider_activity(ticker: str, days: int = 30) -> dict[str, Any]:
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
    """Get demo articles for testing — India-focused."""
    return [
        {
            "id": "demo_in1",
            "title": "Reliance Industries Reports Record Q4 Earnings on Strong Jio Growth",
            "content": "Reliance Industries Ltd reported record quarterly earnings driven by robust growth in Jio Platforms and retail operations. Consolidated revenue rose 11% year-over-year to ₹2.4 lakh crore. Chairman Mukesh Ambani highlighted the digital services segment crossing 480 million subscribers. Refining margins also improved on tight global supply. Analysts maintain a bullish outlook with target prices ranging from ₹2,800-3,200.",
            "source": "ET Markets",
            "url": "https://economictimes.indiatimes.com/reliance-q4",
            "published_at": datetime.utcnow().isoformat(),
        },
        {
            "id": "demo_in2",
            "title": "TCS Wins $2 Billion Deal with Major European Bank",
            "content": "Tata Consultancy Services secured a landmark $2 billion multi-year deal with a leading European financial institution for cloud transformation and AI integration. This is one of the largest deals in Indian IT history. TCS shares rose 3% on the announcement. The deal strengthens TCS's position in the BFSI vertical and is expected to boost revenue growth to double digits in the coming quarters.",
            "source": "Moneycontrol",
            "url": "https://www.moneycontrol.com/tcs-deal",
            "published_at": datetime.utcnow().isoformat(),
        },
        {
            "id": "demo_in3",
            "title": "RBI Holds Repo Rate Steady at 6.5%, Signals Accommodative Stance",
            "content": "The Reserve Bank of India kept the benchmark repo rate unchanged at 6.5% for the eighth consecutive meeting while shifting to an accommodative stance. Governor Das cited easing inflation at 4.2% and resilient GDP growth at 7.6%. The decision supports market expectations of potential rate cuts in the next quarter. Banking stocks rallied with HDFC Bank and ICICI Bank up 2% each on the dovish signal.",
            "source": "LiveMint",
            "url": "https://www.livemint.com/rbi-policy",
            "published_at": datetime.utcnow().isoformat(),
        },
        {
            "id": "demo_in4",
            "title": "NIFTY 50 Hits All-Time High as FII Inflows Surge to ₹15,000 Crore",
            "content": "The NIFTY 50 index surged past 24,000 for the first time, driven by massive foreign institutional investor inflows of ₹15,000 crore in the past week. Broad-based buying was seen across IT, banking, and auto sectors. DII participation remained strong with ₹8,500 crore in net purchases. Market breadth was positive with advances outnumbering declines 3:1 on the NSE. Volatility index India VIX dropped to 11.2, indicating bullish sentiment.",
            "source": "NDTV Profit",
            "url": "https://www.ndtvprofit.com/nifty-high",
            "published_at": datetime.utcnow().isoformat(),
        },
        {
            "id": "demo_in5",
            "title": "HDFC Bank Q3 Results Beat Estimates; Net Profit Rises 33% to ₹16,372 Crore",
            "content": "HDFC Bank reported a 33% jump in standalone net profit to ₹16,372 crore for Q3 FY25, beating analyst estimates of ₹15,800 crore. Net interest income grew 24% to ₹28,470 crore. Asset quality improved with gross NPA ratio declining to 1.26%. The bank's merger integration with HDFC Ltd is progressing ahead of schedule. Shares gained 4% in post-market trading on strong deposit growth of 26%.",
            "source": "Business Standard",
            "url": "https://www.business-standard.com/hdfc-q3",
            "published_at": datetime.utcnow().isoformat(),
        },
    ]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
