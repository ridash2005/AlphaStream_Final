"""
Core RAG pipeline for document processing and retrieval.

Handles chunking, embedding generation, and vector-based retrieval.
"""

import logging
from typing import Any

from src.config import get_settings
from src.pipeline.chunking import AdaptiveChunker
from src.pipeline.retrieval import HybridRetriever, VectorStore, EmbeddingGenerator
from src.pipeline.reranking import Reranker

logger = logging.getLogger(__name__)


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
        self.reranker = Reranker()

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
                "tickers": chunk_data["metadata"]["tickers"],
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
        # 1. Retrieve more candidates than needed (2x)
        candidates = self.retriever.retrieve(query, k=k * 2)
        
        # 2. Rerank candidates with cross-encoder
        final_results = self.reranker.rerank(query, candidates, k=k)
        
        return final_results

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
