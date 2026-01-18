"""
Reranking layer for RAG pipeline.

Uses Cross-Encoders to score query-document pairs for higher accuracy.
"""

import logging
from typing import Any, List, Dict

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    logger.warning("sentence-transformers not installed. Reranking will be skipped.")


class Reranker:
    """
    Reranks documents using a Cross-Encoder model.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.enabled = CROSS_ENCODER_AVAILABLE
        self.model_name = model_name
        self._model = None
        
    @property
    def model(self):
        """Lazy load model."""
        if not self.enabled:
            return None
            
        if self._model is None:
            logger.info(f"Loading reranker model: {self.model_name}")
            try:
                self._model = CrossEncoder(self.model_name)
            except Exception as e:
                logger.error(f"Failed to load reranker model: {e}")
                self.enabled = False
                return None
                
        return self._model

    def rerank(self, query: str, documents: List[Dict[str, Any]], k: int = 5) -> List[Dict[str, Any]]:
        """
        Rerank a list of documents based on query relevance.
        
        Args:
            query: Search query
            documents: List of candidate documents
            k: Number of documents to return after reranking
            
        Returns:
            Top-k reranked documents
        """
        if not self.enabled or not documents or not self.model:
            return documents[:k]

        # Prepare pairs for cross-encoder
        pairs = [[query, doc["text"]] for doc in documents]
        
        try:
            # Predict scores
            scores = self.model.predict(pairs)
            
            # Attach scores and sort
            for i, doc in enumerate(documents):
                doc["rerank_score"] = float(scores[i])
                
            # Sort by new score descending
            reranked = sorted(documents, key=lambda x: x.get("rerank_score", -float('inf')), reverse=True)
            
            return reranked[:k]
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return documents[:k]
