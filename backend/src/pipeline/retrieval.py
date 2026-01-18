"""
Hybrid retrieval system combining dense and sparse search.

Components:
- EmbeddingGenerator: Wraps sentence-transformers
- VectorStore: In-memory dense vector search
- SparseRetriever: BM25 implementation
- HybridRetriever: Combines VectorStore and SparseRetriever using RRF
"""

import logging
import math
from collections import Counter
from typing import Any, List, Dict

import numpy as np

from src.config import get_settings

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not installed. RAG pipeline will fail unless using API embeddings.")


class EmbeddingGenerator:
    """
    Generate embeddings for text using sentence-transformers.
    
    Uses a local model for fast, free embeddings.
    """

    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model
        self._model = None

    @property
    def model(self) -> Any:
        """Lazy load the embedding model."""
        if self._model is None:
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                raise RuntimeError(
                    "sentence-transformers not installed. "
                    "Please install it with: uv pip install sentence-transformers"
                )
            logger.info(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def embedding_dim(self) -> int:
        """Get embedding dimension."""
        return self.model.get_sentence_embedding_dimension()

    def embed(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        return self.model.encode(text, convert_to_numpy=True)

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings for multiple texts."""
        return self.model.encode(texts, convert_to_numpy=True)


class VectorStore:
    """
    In-memory vector store for document retrieval.
    
    Uses cosine similarity for matching.
    """

    def __init__(self, embedding_generator: EmbeddingGenerator):
        self.embedding_generator = embedding_generator
        self.documents: list[dict[str, Any]] = []
        self.embeddings: np.ndarray | None = None

    def add_document(self, doc: dict[str, Any], embedding: np.ndarray | None = None) -> None:
        """Add a document to the store."""
        if embedding is None:
            embedding = self.embedding_generator.embed(doc["text"])

        self.documents.append(doc)

        if self.embeddings is None:
            self.embeddings = embedding.reshape(1, -1)
        else:
            self.embeddings = np.vstack([self.embeddings, embedding.reshape(1, -1)])

    def add_documents(self, docs: list[dict[str, Any]]) -> None:
        """Add multiple documents at once."""
        if not docs:
            return

        texts = [d["text"] for d in docs]
        embeddings = self.embedding_generator.embed_batch(texts)

        for doc, emb in zip(docs, embeddings):
            self.add_document(doc, emb)

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Search for similar documents."""
        if not self.documents or self.embeddings is None:
            return []

        query_embedding = self.embedding_generator.embed(query)

        # Cosine similarity
        similarities = self._cosine_similarity(
            query_embedding.reshape(1, -1), self.embeddings
        )[0]

        # Get top-k indices
        top_k_indices = np.argsort(similarities)[-k:][::-1]

        results = []
        for idx in top_k_indices:
            doc = self.documents[idx].copy()
            doc["similarity"] = float(similarities[idx])
            results.append(doc)

        return results

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Compute cosine similarity between vectors."""
        a_norm = a / np.linalg.norm(a, axis=1, keepdims=True)
        b_norm = b / np.linalg.norm(b, axis=1, keepdims=True)
        return np.dot(a_norm, b_norm.T)

    def clear(self) -> None:
        """Clear all documents from the store."""
        self.documents = []
        self.embeddings = None

    def __len__(self) -> int:
        return len(self.documents)


class SparseRetriever:
    """
    Simple BM25 implementation for sparse retrieval.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: List[Dict[str, Any]] = []
        self.avg_doc_len = 0.0
        self.doc_freqs: List[Dict[str, int]] = []
        self.idf: Dict[str, float] = {}
        self.corpus_size = 0

    def add_documents(self, docs: List[Dict[str, Any]]) -> None:
        """Add documents to the index."""
        if not docs:
            return

        for doc in docs:
            self.documents.append(doc)
            tokens = self._tokenize(doc["text"])
            self.doc_freqs.append(Counter(tokens))

        self.corpus_size = len(self.documents)
        self._calculate_idf()
        self.avg_doc_len = sum(sum(freqs.values()) for freqs in self.doc_freqs) / self.corpus_size

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search using BM25 scoring."""
        if not self.documents:
            return []

        query_tokens = self._tokenize(query)
        scores = np.zeros(self.corpus_size)

        for token in query_tokens:
            if token not in self.idf:
                continue

            idf = self.idf[token]
            
            for i, doc_freqs in enumerate(self.doc_freqs):
                tf = doc_freqs.get(token, 0)
                if tf == 0:
                    continue
                
                doc_len = sum(doc_freqs.values())
                
                # BM25 formula
                numerator = idf * tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_len))
                scores[i] += numerator / denominator

        # Get top-k
        top_indices = np.argsort(scores)[-k:][::-1]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                doc = self.documents[idx].copy()
                doc["score"] = float(scores[idx])
                results.append(doc)
                
        return results

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization (lowercase, simplistic splitting)."""
        return text.lower().split()

    def _calculate_idf(self) -> None:
        """Calculate Inverse Document Frequency."""
        df = Counter()
        for doc_freqs in self.doc_freqs:
            df.update(doc_freqs.keys())

        self.idf = {}
        for token, freq in df.items():
            # Standard IDF + 1 to avoid division by zero
            self.idf[token] = math.log(1 + (self.corpus_size - freq + 0.5) / (freq + 0.5))


class HybridRetriever:
    """
    Combines dense and sparse results using Reciprocal Rank Fusion (RRF).
    """

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.sparse_retriever = SparseRetriever()

    def add_documents(self, docs: List[Dict[str, Any]]) -> None:
        """Add documents to both indices."""
        if not docs:
            return
            
        # Add to sparse index
        self.sparse_retriever.add_documents(docs)
        
        # Add to dense index (VectorStore handles embedding generation)
        self.vector_store.add_documents(docs)

    def retrieve(self, query: str, k: int = 5, rrf_k: int = 60) -> List[Dict[str, Any]]:
        """
        Retrieve using RRF fusion.
        
        Args:
            query: Search query
            k: Final number of results
            rrf_k: Constant for RRF (default 60)
        """
        # Get dense results (fetch more than k for fusion)
        dense_results = self.vector_store.search(query, k=k*2)
        
        # Get sparse results
        sparse_results = self.sparse_retriever.search(query, k=k*2)
        
        # RRF Fusion
        doc_scores = {}  # content -> score
        
        # Helper to identify unique docs (using text hash or content)
        # Using text as key for simplicity since IDs are manual
        
        for rank, doc in enumerate(dense_results):
            key = doc["text"]  # Use text as unique ID for fusion
            if key not in doc_scores:
                doc_scores[key] = {"doc": doc, "score": 0.0}
            doc_scores[key]["score"] += 1.0 / (rrf_k + rank + 1)
            
        for rank, doc in enumerate(sparse_results):
            key = doc["text"]
            if key not in doc_scores:
                doc_scores[key] = {"doc": doc, "score": 0.0}
            doc_scores[key]["score"] += 1.0 / (rrf_k + rank + 1)
            
        # Sort by final score
        sorted_results = sorted(doc_scores.values(), key=lambda x: x["score"], reverse=True)
        
        return [item["doc"] for item in sorted_results[:k]]
