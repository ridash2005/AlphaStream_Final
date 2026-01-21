"""
Unified RAG Service for AlphaStream.

This service provides a unified interface to the RAG system with:
- PRIMARY: Pathway Adaptive RAG (xpacks.llm based)
- FALLBACK: Manual RAG Pipeline (chunking + hybrid retrieval + reranking)

The service automatically falls back to manual RAG if Adaptive RAG is unavailable.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional
import httpx

from src.pipeline.rag_core import RAGPipeline

logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    """Response from RAG query."""
    answer: str
    sources: list[str]
    engine: str  # "adaptive" or "manual"
    latency_ms: float
    documents_retrieved: int


class UnifiedRAGService:
    """
    Unified RAG service with Pathway Adaptive RAG as primary.
    
    Uses Pathway xpacks.llm AdaptiveRAGQuestionAnswerer when available,
    falls back to manual RAGPipeline on failure.
    """
    
    def __init__(
        self,
        adaptive_rag_url: str = "http://localhost:8001",
        manual_rag: Optional[RAGPipeline] = None
    ):
        """
        Initialize the unified RAG service.
        
        Args:
            adaptive_rag_url: URL of the Pathway Adaptive RAG server
            manual_rag: Manual RAG pipeline instance (created if None)
        """
        self.adaptive_rag_url = adaptive_rag_url
        self.manual_rag = manual_rag or RAGPipeline()
        
        # Metrics
        self.adaptive_queries = 0
        self.manual_queries = 0
        self.adaptive_failures = 0
        
        logger.info(f"UnifiedRAGService initialized")
        logger.info(f"  Primary: Pathway Adaptive RAG at {adaptive_rag_url}")
        logger.info(f"  Fallback: Manual RAG Pipeline")
    
    def query(self, question: str, ticker: Optional[str] = None) -> RAGResponse:
        """
        Query the RAG system.
        
        Tries Pathway Adaptive RAG first, falls back to manual on failure.
        
        Args:
            question: The query question
            ticker: Optional ticker symbol for context
            
        Returns:
            RAGResponse with answer, sources, and metadata
        """
        start_time = time.time()
        
        # Format question with ticker context
        full_question = question
        if ticker:
            full_question = f"For {ticker}: {question}"
        
        # Try Adaptive RAG first
        try:
            response = self._query_adaptive_rag(full_question)
            self.adaptive_queries += 1
            logger.info(f"[Adaptive RAG] Query successful in {response.latency_ms:.0f}ms")
            return response
        except Exception as e:
            self.adaptive_failures += 1
            logger.warning(f"[Adaptive RAG] Failed: {e}")
            logger.info("[Manual RAG] Falling back to manual pipeline")
        
        # Fallback to manual RAG
        response = self._query_manual_rag(full_question)
        self.manual_queries += 1
        logger.info(f"[Manual RAG] Query successful in {response.latency_ms:.0f}ms")
        return response
    
    def _query_adaptive_rag(self, question: str) -> RAGResponse:
        """
        Query the Pathway Adaptive RAG server.
        
        Uses the /v2/answer endpoint from QASummaryRestServer.
        """
        start_time = time.time()
        
        # Make HTTP request to Adaptive RAG server
        # Note: Pathway's QASummaryRestServer expects "prompt" key, not "query"
        # Timeout increased to 60s to handle slower LLM responses
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{self.adaptive_rag_url}/v2/answer",
                json={"prompt": question}
            )
            response.raise_for_status()
            data = response.json()
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Pathway returns "response" key, not "answer"
        return RAGResponse(
            answer=data.get("response", data.get("answer", "")),
            sources=data.get("sources", []),
            engine="adaptive",
            latency_ms=latency_ms,
            documents_retrieved=data.get("documents_retrieved", 0)
        )
    
    def _query_manual_rag(self, question: str) -> RAGResponse:
        """
        Query using the manual RAG pipeline.
        """
        start_time = time.time()
        
        # Retrieve relevant documents
        documents = self.manual_rag.retrieve(question, k=5)
        
        # Format context
        context = self.manual_rag.format_context(documents)
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Extract sources
        sources = list(set(doc.get("source", "Unknown") for doc in documents))
        
        return RAGResponse(
            answer=context,  # Raw context for agent to process
            sources=sources,
            engine="manual",
            latency_ms=latency_ms,
            documents_retrieved=len(documents)
        )
    
    def ingest_article(self, article: dict) -> int:
        """
        Ingest an article into the manual RAG pipeline.
        
        Note: For Adaptive RAG, articles should be written to the
        data/articles directory for automatic ingestion.
        
        Args:
            article: Article dict with title, content, etc.
            
        Returns:
            Number of chunks created
        """
        return self.manual_rag.ingest_article(article)
    
    def ingest_articles(self, articles: list[dict]) -> int:
        """Ingest multiple articles."""
        return self.manual_rag.ingest_articles(articles)
    
    def get_stats(self) -> dict:
        """Get service statistics."""
        total_queries = self.adaptive_queries + self.manual_queries
        return {
            "total_queries": total_queries,
            "adaptive_queries": self.adaptive_queries,
            "manual_queries": self.manual_queries,
            "adaptive_failures": self.adaptive_failures,
            "adaptive_success_rate": (
                self.adaptive_queries / (self.adaptive_queries + self.adaptive_failures)
                if (self.adaptive_queries + self.adaptive_failures) > 0
                else 0.0
            ),
            "primary_engine": "Pathway Adaptive RAG",
            "fallback_engine": "Manual RAG Pipeline",
            "document_count": self.manual_rag.document_count
        }
    
    def is_adaptive_available(self) -> bool:
        """Check if Adaptive RAG server is available."""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.adaptive_rag_url}/health")
                return response.status_code == 200
        except Exception:
            return False


# Singleton instance
_unified_rag_service: Optional[UnifiedRAGService] = None


def get_unified_rag_service() -> UnifiedRAGService:
    """Get or create the unified RAG service singleton."""
    global _unified_rag_service
    if _unified_rag_service is None:
        _unified_rag_service = UnifiedRAGService()
    return _unified_rag_service
