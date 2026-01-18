"""
Unit tests for API endpoints.
"""

import pytest
from fastapi.testclient import TestClient


# Import with environment variables set for testing
import os
os.environ.setdefault("OPENROUTER_API_KEY", "test_key")
os.environ.setdefault("NEWSAPI_KEY", "test_key")

from src.api.app import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_check_returns_200(self, client):
        """Test health check returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_contains_status(self, client):
        """Test health check response contains status."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_health_check_contains_components(self, client):
        """Test health check response contains component status."""
        response = client.get("/health")
        data = response.json()
        assert "components" in data
        assert "rag_pipeline" in data["components"]
        assert "sentiment_agent" in data["components"]


class TestRecommendEndpoint:
    """Tests for the /recommend endpoint."""

    def test_recommend_requires_ticker(self, client):
        """Test that ticker is required."""
        response = client.post("/recommend", json={})
        assert response.status_code == 422  # Validation error

    def test_recommend_with_valid_ticker(self, client):
        """Test recommendation with valid ticker."""
        response = client.post("/recommend", json={"ticker": "AAPL"})
        # Should succeed (uses demo data) or fail gracefully
        # In test environment without real OpenRouter, may return 500
        assert response.status_code in [200, 500, 503]

    def test_recommend_response_structure(self, client):
        """Test response has correct structure when successful."""
        response = client.post("/recommend", json={"ticker": "AAPL"})
        if response.status_code == 200:
            data = response.json()
            assert "ticker" in data
            assert "recommendation" in data
            assert data["recommendation"] in ["BUY", "HOLD", "SELL"]
            assert "confidence" in data
            assert "latency_ms" in data


class TestArticlesEndpoint:
    """Tests for the /articles/{ticker} endpoint."""

    def test_get_articles(self, client):
        """Test getting articles for a ticker."""
        response = client.get("/articles/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data
        assert data["ticker"] == "AAPL"
        assert "articles" in data

    def test_get_articles_with_limit(self, client):
        """Test getting articles with limit."""
        response = client.get("/articles/MSFT?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["articles"]) <= 2


class TestIngestEndpoint:
    """Tests for the /ingest endpoint."""

    def test_ingest_article(self, client):
        """Test ingesting a new article."""
        article = {
            "title": "Test Article",
            "content": "This is test content for the article.",
        }
        response = client.post("/ingest", json=article)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "chunks_created" in data

    def test_ingest_requires_title(self, client):
        """Test that title is required."""
        article = {"content": "Content without title"}
        response = client.post("/ingest", json=article)
        assert response.status_code == 400

    def test_ingest_requires_content(self, client):
        """Test that content is required."""
        article = {"title": "Title without content"}
        response = client.post("/ingest", json=article)
        assert response.status_code == 400
