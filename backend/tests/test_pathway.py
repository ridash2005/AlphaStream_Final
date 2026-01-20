"""
Tests for Pathway-related modules.

Tests cover:
- UnifiedRAGService (Adaptive RAG primary, manual fallback)
- PathwayTables (streaming data schemas)
- RAG Service integration
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestUnifiedRAGService:
    """Tests for the UnifiedRAGService."""
    
    def test_service_initialization(self):
        """Test that UnifiedRAGService initializes correctly."""
        from src.pipeline.rag_service import UnifiedRAGService
        from src.pipeline.rag_core import RAGPipeline
        
        manual_rag = RAGPipeline()
        service = UnifiedRAGService(
            adaptive_rag_url="http://localhost:8001",
            manual_rag=manual_rag
        )
        
        assert service.adaptive_rag_url == "http://localhost:8001"
        assert service.manual_rag is manual_rag
        assert service.adaptive_queries == 0
        assert service.manual_queries == 0
        
    def test_fallback_to_manual_when_adaptive_unavailable(self):
        """Test that service falls back to manual RAG when adaptive is unavailable."""
        from src.pipeline.rag_service import UnifiedRAGService
        from src.pipeline.rag_core import RAGPipeline
        
        # Create a mock that will fail for adaptive RAG
        manual_rag = RAGPipeline()
        service = UnifiedRAGService(
            adaptive_rag_url="http://nonexistent:9999",  # Won't be reachable
            manual_rag=manual_rag
        )
        
        # Seed some data
        manual_rag.ingest_article({
            "title": "Test Article",
            "content": "AAPL stock is performing well today with strong earnings.",
            "source": "Test Source",
            "id": "test-1"
        })
        
        # Query should fall back to manual
        response = service.query("AAPL stock news", ticker="AAPL")
        
        assert response.engine == "manual"
        assert service.manual_queries == 1
        assert service.adaptive_failures == 1
        
    def test_rag_response_structure(self):
        """Test that RAGResponse has correct structure."""
        from src.pipeline.rag_service import RAGResponse
        
        response = RAGResponse(
            answer="Test answer",
            sources=["source1", "source2"],
            engine="adaptive",
            latency_ms=150.5,
            documents_retrieved=3
        )
        
        assert response.answer == "Test answer"
        assert len(response.sources) == 2
        assert response.engine == "adaptive"
        assert response.latency_ms == 150.5
        assert response.documents_retrieved == 3
        
    def test_get_stats(self):
        """Test statistics tracking."""
        from src.pipeline.rag_service import UnifiedRAGService
        from src.pipeline.rag_core import RAGPipeline
        
        manual_rag = RAGPipeline()
        service = UnifiedRAGService(
            adaptive_rag_url="http://localhost:8001",
            manual_rag=manual_rag
        )
        
        stats = service.get_stats()
        
        assert "total_queries" in stats
        assert "adaptive_queries" in stats
        assert "manual_queries" in stats
        assert "primary_engine" in stats
        assert stats["primary_engine"] == "Pathway Adaptive RAG"
        assert stats["fallback_engine"] == "Manual RAG Pipeline"


class TestPathwayTables:
    """Tests for Pathway streaming tables."""
    
    def test_news_schema_import(self):
        """Test that Pathway schemas can be imported."""
        try:
            from src.pipeline.pathway_tables import NewsArticleSchema, MarketEventSchema
            assert True
        except ImportError as e:
            # Pathway might not be installed in test environment
            pytest.skip(f"Pathway not available: {e}")
            
    def test_pathway_import(self):
        """Test Pathway core import."""
        try:
            import pathway as pw
            assert hasattr(pw, 'Schema')
            assert hasattr(pw, 'Table')
            assert hasattr(pw, 'io')
        except ImportError:
            pytest.skip("Pathway not installed")
            
    def test_connector_subject_available(self):
        """Test that ConnectorSubject is available for streaming ingestion."""
        try:
            from pathway.io.python import ConnectorSubject
            assert True
        except ImportError:
            pytest.skip("Pathway io.python not available")


class TestAdaptiveRAGComponents:
    """Tests for Adaptive RAG server components."""
    
    def test_adaptive_rag_app_import(self):
        """Test that AdaptiveRAGApp can be imported."""
        try:
            from src.pipeline.adaptive_rag_server import AdaptiveRAGApp
            assert True
        except ImportError as e:
            pytest.skip(f"Could not import: {e}")
            
    def test_pathway_rag_metrics(self):
        """Test PathwayRAGMetrics class."""
        from src.pipeline.adaptive_rag_server import PathwayRAGMetrics
        
        metrics = PathwayRAGMetrics()
        assert metrics.queries_processed == 0
        assert metrics.documents_indexed == 0
        
        stats = metrics.get_stats()
        assert "engine" in stats
        assert stats["engine"] == "Pathway Adaptive RAG"
        assert "xpacks_used" in stats
        assert len(stats["xpacks_used"]) > 0


class TestRAGPipelineIntegration:
    """Integration tests for RAG pipeline."""
    
    def test_ingest_and_retrieve(self):
        """Test basic ingest and retrieve flow."""
        from src.pipeline.rag_core import RAGPipeline
        
        pipeline = RAGPipeline()
        
        # Ingest test article
        chunks = pipeline.ingest_article({
            "title": "Apple Announces Record Earnings",
            "content": """
            Apple Inc. today announced record quarterly revenue of $123 billion,
            driven by strong iPhone and Services sales. CEO Tim Cook stated that
            customer satisfaction remains at all-time highs.
            """,
            "source": "Test News",
            "id": "test-apple-1"
        })
        
        assert chunks > 0
        
        # Retrieve
        results = pipeline.retrieve("Apple earnings news", k=3)
        assert len(results) > 0
        assert any("Apple" in r.get("text", "") for r in results)
        
    def test_format_context(self):
        """Test context formatting for LLM."""
        from src.pipeline.rag_core import RAGPipeline
        
        pipeline = RAGPipeline()
        
        docs = [
            {"title": "Test 1", "text": "Content 1", "source": "Source A"},
            {"title": "Test 2", "text": "Content 2", "source": "Source B"},
        ]
        
        context = pipeline.format_context(docs)
        
        assert "Test 1" in context
        assert "Content 1" in context
        assert "Source A" in context
        assert "[Source 1]" in context
        

class TestPathwayFeatures:
    """Tests to verify Pathway features are used correctly."""
    
    def test_pathway_features_documented(self):
        """Verify key Pathway features are documented in code."""
        import os
        
        # Check adaptive_rag_server.py for Pathway features
        rag_server_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'src', 'pipeline', 'adaptive_rag_server.py'
        )
        
        with open(rag_server_path, 'r') as f:
            content = f.read()
        
        # Check for key Pathway imports/features
        pathway_features = [
            "pathway",
            "pw.xpacks.llm",
            "AdaptiveRAGQuestionAnswerer",
            "DocumentStore",
            "UsearchKnnFactory",
            "pw.run",
        ]
        
        for feature in pathway_features:
            assert feature in content, f"Missing Pathway feature: {feature}"
            
    def test_pathway_tables_has_schemas(self):
        """Verify pathway_tables.py has proper schemas."""
        import os
        
        tables_path = os.path.join(
            os.path.dirname(__file__),
            '..', 'src', 'pipeline', 'pathway_tables.py'
        )
        
        with open(tables_path, 'r') as f:
            content = f.read()
        
        # Check for schema patterns
        assert "pw.Schema" in content or "Schema" in content
        assert "class" in content  # Should have schema classes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
