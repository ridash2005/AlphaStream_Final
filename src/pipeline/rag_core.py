"""
Core RAG pipeline for document processing and retrieval.

Handles chunking, embedding generation, and vector-based retrieval.
"""

import logging
from typing import Any

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not installed. RAG pipeline will fail unless using API embeddings.")

from src.config import get_settings
from src.pipeline.chunking import AdaptiveChunker
from src.pipeline.retrieval import HybridRetriever

logger = logging.getLogger(__name__)





class EmbeddingGenerator:
    """
    Generate embeddings for text using sentence-transformers.
    
    Uses a local model for fast, free embeddings.
    """

    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model
        self._model: SentenceTransformer | None = None

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
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Numpy array of embedding
        """
        return self.model.encode(text, convert_to_numpy=True)

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            Numpy array of embeddings (N x dim)
        """
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
        """
        Add a document to the store.

        Args:
            doc: Document dict with 'text' and metadata
            embedding: Pre-computed embedding (optional)
        """
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
        """
        Search for similar documents.

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            List of document dicts with similarity scores
        """
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


class RAGPipeline:
    """
    Complete RAG pipeline: chunk, embed, store, retrieve.
    """

    def __init__(self):
        self.chunk_processor = AdaptiveChunker()
        self.embedding_generator = EmbeddingGenerator()
        
        # Initialize lower-level stores
        self.vector_store = VectorStore(self.embedding_generator)
        
        # High-level retriever
        self.retriever = HybridRetriever(self.vector_store)

    def ingest_article(self, article: dict[str, Any]) -> int:
        """
        Ingest a single article into the RAG pipeline.

        Args:
            article: Article dict with title, content, source, etc.

        Returns:
            Number of chunks created
        """
        # Combine title and content for better context
        # chunk_document handles combination internally if needed, but we pass title explicitly
        chunks_data = self.chunk_processor.chunk_document(article.get('content', ''), article.get('title', ''))

        docs = []
        for i, chunk_data in enumerate(chunks_data):
            docs.append({
                "text": chunk_data["text"],
                "article_id": article.get("id", ""),
                "title": article.get("title", ""),
                "source": article.get("source", ""),
                "url": article.get("url", ""),
                "published_at": article.get("published_at", ""),
                "chunk_index": i,
                "tickers": chunk_data["metadata"]["tickers"],  # New field
            })

        self.retriever.add_documents(docs)
        return len(chunks_data)

    def ingest_articles(self, articles: list[dict[str, Any]]) -> int:
        """
        Ingest multiple articles.

        Args:
            articles: List of article dicts

        Returns:
            Total number of chunks created
        """
        total_chunks = 0
        for article in articles:
            total_chunks += self.ingest_article(article)
        logger.info(f"Ingested {len(articles)} articles into {total_chunks} chunks")
        return total_chunks

    def retrieve(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: Search query
            k: Number of documents to retrieve

        Returns:
            List of relevant document chunks
        """
        return self.retriever.retrieve(query, k=k)

    def format_context(self, documents: list[dict[str, Any]]) -> str:
        """
        Format retrieved documents into context string for LLM.

        Args:
            documents: List of retrieved documents

        Returns:
            Formatted context string
        """
        context_parts = []
        for i, doc in enumerate(documents, 1):
            context_parts.append(
                f"[Source {i}] {doc.get('title', 'Unknown')} ({doc.get('source', 'Unknown')})\n"
                f"{doc.get('text', '')}\n"
            )
        return "\n".join(context_parts)

    @property
    def document_count(self) -> int:
        """Get number of documents in the store."""
        return len(self.vector_store)
