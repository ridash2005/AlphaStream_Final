"""
Tests for NewsAPI connector.
"""

import pytest
from unittest.mock import Mock, patch
from src.connectors.news_connector import NewsAPISubject, NewsArticleSchema


class TestNewsConnector:
    @pytest.fixture
    def mock_response(self):
        return {
            "status": "ok",
            "articles": [
                {
                    "title": "Test Article 1",
                    "description": "Desc 1",
                    "url": "http://test.com/1",
                    "source": {"name": "Test Source"},
                    "publishedAt": "2023-01-01T00:00:00Z"
                },
                {
                    "title": "Test Article 2",
                    "description": "Desc 2",
                    "url": "http://test.com/2",
                    "source": {"name": "Test Source"},
                    "publishedAt": "2023-01-01T00:00:00Z"
                }
            ]
        }

    def test_deduplication(self, mock_response):
        """Test that connector deduplicates articles."""
        subject = NewsAPISubject(api_key="test_key", refresh_interval=1)
        
        # Mock requests.get
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response
            
            # First fetch
            articles_batch1 = subject._fetch_articles()
            count1 = 0
            for article in articles_batch1:
                aid = subject._generate_id(article)
                if aid not in subject.seen_ids:
                    subject.seen_ids.add(aid)
                    count1 += 1
            
            assert count1 == 2
            
            # Second fetch (same data)
            articles_batch2 = subject._fetch_articles()
            count2 = 0
            for article in articles_batch2:
                aid = subject._generate_id(article)
                if aid not in subject.seen_ids:
                    subject.seen_ids.add(aid)
                    count2 += 1
            
            assert count2 == 0  # Should be duplicates

    def test_id_generation(self):
        """Test consistent ID generation."""
        subject = NewsAPISubject(api_key="test")
        article = {"title": "Test", "url": "http://test.com"}
        
        id1 = subject._generate_id(article)
        id2 = subject._generate_id(article)
        
        assert id1 == id2
        assert isinstance(id1, str)
        assert len(id1) > 0
