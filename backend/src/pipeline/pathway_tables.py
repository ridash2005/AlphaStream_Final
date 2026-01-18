"""
Pathway-Native Tables for AlphaStream Live AI.

This module leverages Pathway's streaming data processing capabilities
to provide real-time market intelligence with automatic updates.

Key Pathway Features Used:
- pw.Table: Streaming tables for market data
- pw.apply: Transform functions applied to streams
- pw.temporal: Time-based operations
- pw.reducers: Aggregations over streaming windows
"""

import logging
from datetime import datetime
from typing import Any

import pathway as pw
from pathway import reducers

logger = logging.getLogger(__name__)


# =============================================================================
# PATHWAY SCHEMAS
# =============================================================================

class MarketSentimentSchema(pw.Schema):
    """Schema for real-time market sentiment tracking."""
    ticker: str = pw.column_definition(primary_key=True)
    sentiment_score: float
    sentiment_label: str  # BULLISH, NEUTRAL, BEARISH
    confidence: float
    source_count: int
    last_updated: str


class ArticleSchema(pw.Schema):
    """Schema for processed articles in the RAG pipeline."""
    article_id: str = pw.column_definition(primary_key=True)
    title: str
    content: str
    source: str
    ticker_mentions: str  # Comma-separated tickers
    sentiment: float
    processed_at: str


class AlertSchema(pw.Schema):
    """Schema for real-time trading alerts."""
    alert_id: str = pw.column_definition(primary_key=True)
    ticker: str
    alert_type: str  # SENTIMENT_SPIKE, INSIDER_ACTIVITY, PRICE_MOVE
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    message: str
    created_at: str


# =============================================================================
# PATHWAY TRANSFORMATIONS
# =============================================================================

def sentiment_to_label(score: float) -> str:
    """Convert sentiment score to label using Pathway UDF."""
    if score > 0.3:
        return "BULLISH"
    elif score < -0.3:
        return "BEARISH"
    return "NEUTRAL"


def extract_tickers(content: str) -> str:
    """Extract ticker symbols from content."""
    import re
    # Common tickers - extend as needed
    known_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "AMD"]
    found = [t for t in known_tickers if t in content.upper()]
    return ",".join(found) if found else ""


def create_alert_message(ticker: str, alert_type: str, data: dict) -> str:
    """Generate alert message based on type."""
    if alert_type == "SENTIMENT_SPIKE":
        return f"Sentiment spike detected for {ticker}: {data.get('sentiment', 0):.2f}"
    elif alert_type == "INSIDER_ACTIVITY":
        return f"Insider trading activity detected for {ticker}"
    elif alert_type == "PRICE_MOVE":
        return f"Significant price movement for {ticker}: {data.get('change', 0):.1f}%"
    return f"Alert for {ticker}: {alert_type}"


# =============================================================================
# PATHWAY TABLE FACTORY
# =============================================================================

class PathwayTableManager:
    """
    Manages Pathway streaming tables for real-time market intelligence.
    
    This class provides a centralized way to create and manage Pathway
    tables that automatically update as new data arrives.
    """
    
    def __init__(self):
        self.sentiment_table: pw.Table | None = None
        self.article_table: pw.Table | None = None
        self.alert_table: pw.Table | None = None
        
        logger.info("PathwayTableManager initialized")
    
    def create_sentiment_table(self, initial_data: list[dict] = None) -> pw.Table:
        """
        Create a Pathway table for market sentiment tracking.
        
        This table automatically updates as new sentiment data arrives,
        providing real-time aggregations and alerts.
        """
        if initial_data is None:
            initial_data = []
        
        # Create table from initial data
        rows = [
            (
                d.get("ticker", ""),
                d.get("sentiment_score", 0.0),
                d.get("sentiment_label", "NEUTRAL"),
                d.get("confidence", 0.0),
                d.get("source_count", 0),
                d.get("last_updated", datetime.utcnow().isoformat())
            )
            for d in initial_data
        ]
        
        self.sentiment_table = pw.debug.table_from_rows(
            schema=MarketSentimentSchema,
            rows=rows if rows else [("INIT", 0.0, "NEUTRAL", 0.0, 0, datetime.utcnow().isoformat())]
        )
        
        logger.info(f"Created sentiment table with {len(rows)} initial rows")
        return self.sentiment_table
    
    def create_article_processing_pipeline(self, source_table: pw.Table) -> pw.Table:
        """
        Create a Pathway pipeline for article processing.
        
        Applies transformations to extract tickers and sentiment,
        demonstrating pw.apply usage.
        """
        # Apply ticker extraction using pw.apply
        processed = source_table.select(
            article_id=pw.this.id,
            title=pw.this.title,
            content=pw.this.content,
            source=pw.this.source,
            ticker_mentions=pw.apply(extract_tickers, pw.this.content),
            sentiment=pw.this.sentiment if hasattr(pw.this, 'sentiment') else 0.0,
            processed_at=pw.apply(lambda: datetime.utcnow().isoformat())
        )
        
        self.article_table = processed
        logger.info("Created article processing pipeline with Pathway transformations")
        return processed
    
    def create_sentiment_aggregation(self, article_table: pw.Table) -> pw.Table:
        """
        Aggregate sentiment by ticker using Pathway reducers.
        
        Demonstrates pw.reducers for real-time aggregations.
        """
        # Group by ticker and aggregate sentiment
        aggregated = article_table.groupby(
            pw.this.ticker_mentions
        ).reduce(
            ticker=pw.this.ticker_mentions,
            avg_sentiment=reducers.avg(pw.this.sentiment),
            article_count=reducers.count(),
            max_sentiment=reducers.max(pw.this.sentiment),
            min_sentiment=reducers.min(pw.this.sentiment)
        )
        
        logger.info("Created sentiment aggregation pipeline")
        return aggregated
    
    def create_alert_generator(self, sentiment_table: pw.Table, threshold: float = 0.7) -> pw.Table:
        """
        Generate alerts based on sentiment changes.
        
        Uses pw.filter to detect significant events.
        """
        # Filter for high-sentiment events
        high_sentiment = sentiment_table.filter(
            pw.abs(pw.this.sentiment_score) > threshold
        )
        
        # Transform to alerts
        alerts = high_sentiment.select(
            alert_id=pw.apply(lambda t: f"alert_{t}_{datetime.utcnow().timestamp()}", pw.this.ticker),
            ticker=pw.this.ticker,
            alert_type="SENTIMENT_SPIKE",
            severity=pw.apply(
                lambda s: "CRITICAL" if abs(s) > 0.9 else "HIGH" if abs(s) > 0.8 else "MEDIUM",
                pw.this.sentiment_score
            ),
            message=pw.apply(
                lambda t, s: f"Sentiment spike for {t}: {s:.2f}",
                pw.this.ticker, pw.this.sentiment_score
            ),
            created_at=pw.apply(lambda: datetime.utcnow().isoformat())
        )
        
        self.alert_table = alerts
        logger.info("Created alert generator pipeline")
        return alerts


# =============================================================================
# PATHWAY METRICS
# =============================================================================

class PathwayMetrics:
    """
    Tracks Pathway engine performance metrics.
    """
    
    def __init__(self):
        self.messages_processed = 0
        self.tables_created = 0
        self.last_update = None
    
    def record_message(self):
        self.messages_processed += 1
        self.last_update = datetime.utcnow().isoformat()
    
    def record_table(self):
        self.tables_created += 1
    
    def get_stats(self) -> dict:
        return {
            "messages_processed": self.messages_processed,
            "tables_created": self.tables_created,
            "last_update": self.last_update,
            "status": "running"
        }


# Singleton instances
_table_manager: PathwayTableManager | None = None
_metrics: PathwayMetrics | None = None


def get_table_manager() -> PathwayTableManager:
    """Get or create the Pathway table manager singleton."""
    global _table_manager
    if _table_manager is None:
        _table_manager = PathwayTableManager()
    return _table_manager


def get_pathway_metrics() -> PathwayMetrics:
    """Get or create the Pathway metrics singleton."""
    global _metrics
    if _metrics is None:
        _metrics = PathwayMetrics()
    return _metrics
