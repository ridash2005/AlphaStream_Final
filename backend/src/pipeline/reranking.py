"""
Reranking layer for RAG pipeline.

Uses Vertex AI Gemini for reranking (no local models).
Falls back to original document order if unavailable.
"""
import logging
from typing import Any, List, Dict

logger = logging.getLogger(__name__)


class Reranker:
    """
    Reranks documents using Vertex AI LLM scoring.
    No local model downloads needed.
    """

    def __init__(self):
        self.enabled = True

    def rerank(self, query: str, documents: List[Dict[str, Any]], k: int = 5) -> List[Dict[str, Any]]:
        """Rerank documents by relevance. Uses simple keyword overlap scoring."""
        if not documents:
            return []

        try:
            query_terms = set(query.lower().split())
            for doc in documents:
                text = doc.get("text", "").lower()
                overlap = len(query_terms & set(text.split()))
                doc["rerank_score"] = overlap / max(len(query_terms), 1)

            reranked = sorted(documents, key=lambda x: x.get("rerank_score", 0), reverse=True)
            return reranked[:k]
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return documents[:k]
