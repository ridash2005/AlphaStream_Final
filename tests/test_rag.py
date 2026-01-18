"""
Unit tests for RAG pipeline components.
"""

import pytest
import numpy as np

from src.pipeline.rag_core import ChunkProcessor, EmbeddingGenerator, VectorStore, RAGPipeline


class TestChunkProcessor:
    """Tests for the ChunkProcessor class."""

    def test_chunk_empty_text(self):
        """Test chunking empty text returns empty list."""
        processor = ChunkProcessor()
        assert processor.chunk_text("") == []
        assert processor.chunk_text("   ") == []

    def test_chunk_single_sentence(self):
        """Test chunking a single short sentence."""
        processor = ChunkProcessor(max_chunk_size=100)
        text = "This is a simple sentence."
        chunks = processor.chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_multiple_sentences(self):
        """Test chunking multiple sentences into one chunk when under limit."""
        processor = ChunkProcessor(max_chunk_size=100)
        text = "First sentence. Second sentence. Third sentence."
        chunks = processor.chunk_text(text)
        assert len(chunks) == 1

    def test_chunk_long_text_splits(self):
        """Test that long text is split into multiple chunks."""
        processor = ChunkProcessor(max_chunk_size=10)
        text = "This is a long sentence that should be split. Another sentence here. And one more."
        chunks = processor.chunk_text(text)
        assert len(chunks) > 1

    def test_chunk_preserves_content(self):
        """Test that all content is preserved after chunking."""
        processor = ChunkProcessor(max_chunk_size=20)
        text = "Apple reported strong earnings. Microsoft also beat expectations. Tesla had a mixed quarter."
        chunks = processor.chunk_text(text)
        
        # Rejoin and compare word count
        original_words = set(text.lower().replace(".", "").split())
        chunked_words = set(" ".join(chunks).lower().replace(".", "").split())
        assert original_words == chunked_words


class TestEmbeddingGenerator:
    """Tests for the EmbeddingGenerator class."""

    @pytest.fixture
    def generator(self):
        """Create an embedding generator with fast model."""
        return EmbeddingGenerator(model_name="sentence-transformers/all-MiniLM-L6-v2")

    def test_embed_single_text(self, generator):
        """Test embedding a single text."""
        embedding = generator.embed("This is a test.")
        assert isinstance(embedding, np.ndarray)
        assert len(embedding.shape) == 1
        assert embedding.shape[0] == generator.embedding_dim

    def test_embed_batch(self, generator):
        """Test embedding multiple texts."""
        texts = ["First text.", "Second text.", "Third text."]
        embeddings = generator.embed_batch(texts)
        assert embeddings.shape[0] == 3
        assert embeddings.shape[1] == generator.embedding_dim

    def test_similar_texts_have_high_similarity(self, generator):
        """Test that similar texts have higher cosine similarity."""
        text1 = "Apple stock price increased today."
        text2 = "Apple shares went up in trading."
        text3 = "The weather is nice outside."

        emb1 = generator.embed(text1)
        emb2 = generator.embed(text2)
        emb3 = generator.embed(text3)

        # Cosine similarity
        sim_12 = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        sim_13 = np.dot(emb1, emb3) / (np.linalg.norm(emb1) * np.linalg.norm(emb3))

        # Similar texts should have higher similarity
        assert sim_12 > sim_13


class TestVectorStore:
    """Tests for the VectorStore class."""

    @pytest.fixture
    def store(self):
        """Create a vector store with embedding generator."""
        generator = EmbeddingGenerator(model_name="sentence-transformers/all-MiniLM-L6-v2")
        return VectorStore(generator)

    def test_add_and_search(self, store):
        """Test adding documents and searching."""
        docs = [
            {"text": "Apple reported strong earnings.", "source": "Reuters"},
            {"text": "Microsoft cloud revenue increased.", "source": "CNBC"},
            {"text": "Tesla deliveries missed expectations.", "source": "Bloomberg"},
        ]
        store.add_documents(docs)

        results = store.search("Apple financial results", k=2)
        assert len(results) == 2
        assert results[0]["text"] == "Apple reported strong earnings."
        assert "similarity" in results[0]

    def test_search_empty_store(self, store):
        """Test searching an empty store returns empty list."""
        results = store.search("test query")
        assert results == []

    def test_document_count(self, store):
        """Test document count is tracked correctly."""
        assert len(store) == 0
        store.add_document({"text": "Test document"})
        assert len(store) == 1

    def test_clear_store(self, store):
        """Test clearing the store."""
        store.add_document({"text": "Test document"})
        assert len(store) == 1
        store.clear()
        assert len(store) == 0


class TestRAGPipeline:
    """Tests for the complete RAG pipeline."""

    @pytest.fixture
    def pipeline(self):
        """Create a RAG pipeline."""
        return RAGPipeline()

    def test_ingest_article(self, pipeline):
        """Test ingesting a single article."""
        article = {
            "id": "test1",
            "title": "Apple Earnings Beat",
            "content": "Apple Inc. reported better than expected quarterly earnings.",
            "source": "Reuters",
        }
        chunks = pipeline.ingest_article(article)
        assert chunks > 0
        assert pipeline.document_count > 0

    def test_ingest_and_retrieve(self, pipeline):
        """Test full ingest and retrieve cycle."""
        articles = [
            {
                "id": "1",
                "title": "Apple Revenue Grows",
                "content": "Apple reported 10% revenue growth driven by iPhone sales.",
                "source": "Reuters",
            },
            {
                "id": "2",
                "title": "Tesla Production Update",
                "content": "Tesla increased production at its Gigafactory.",
                "source": "Bloomberg",
            },
        ]
        pipeline.ingest_articles(articles)

        results = pipeline.retrieve("Apple financial performance")
        assert len(results) > 0
        # Apple article should be most relevant
        assert "Apple" in results[0]["title"]

    def test_format_context(self, pipeline):
        """Test context formatting for LLM."""
        docs = [
            {"title": "Test Title", "source": "Test Source", "text": "Test content."},
        ]
        context = pipeline.format_context(docs)
        assert "Test Title" in context
        assert "Test Source" in context
        assert "Test content" in context
