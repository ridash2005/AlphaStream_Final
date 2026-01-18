"""
Tests for Multi-Agent System.
"""

import pytest
from unittest.mock import MagicMock, patch
from src.agents.sentiment_agent import SentimentAgent
from src.agents.technical_agent import TechnicalAgent
from src.agents.risk_agent import RiskAgent
from src.agents.decision_agent import DecisionAgent


class TestAgents:
    
    @pytest.fixture
    def mock_llm_response(self):
        return {
            "choices": [{
                "message": {
                    "content": '{"sentiment_score": 0.8, "sentiment_label": "BULLISH", "confidence": 0.9, "key_factors": ["Growth"]}'
                }
            }]
        }

    @patch('src.agents.sentiment_agent.OpenAI')
    def test_sentiment_agent(self, mock_openai, mock_llm_response):
        """Test sentiment agent analysis."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(**mock_llm_response)
        
        agent = SentimentAgent()
        result = agent.analyze([{"title": "Good News", "content": "Stock is up"}])
        
        assert result["sentiment_label"] == "BULLISH"
        assert result["sentiment_score"] == 0.8

    @patch('src.agents.technical_agent.yf')
    def test_technical_agent(self, mock_yf):
        """Test technical agent with mock data."""
        # Setup mock history
        import pandas as pd
        mock_hist = pd.DataFrame({
            "Close": [100.0, 101.0, 102.0] * 20  # Enough for SMA?
        })
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_hist
        mock_yf.Ticker.return_value = mock_ticker
        
        # We need more data for indicators (SMA20, SMA50)
        # Using the internal mock fallback might be easier if we simulate import error or empty data
        # But let's test the fallback path directly by mocking _get_price_data
        
        agent = TechnicalAgent()
        with patch.object(agent, '_get_price_data') as mock_get_data:
            # Create a mock dataframe with enough data
            dates = pd.date_range(start='2023-01-01', periods=60)
            df = pd.DataFrame(index=dates)
            df['Close'] = [100 + i for i in range(60)] # Uptrend
            mock_get_data.return_value = df
            
            result = agent.analyze("AAPL")
            
            assert "signal" in result
            assert "indicators" in result
            assert result["indicators"]["sma_50"] > 0

    def test_risk_agent(self):
        """Test risk agent logic."""
        agent = RiskAgent()
        technical_data = {
            "indicators": {
                "price": 100.0,
                "rsi": 80.0 # High risk
            }
        }
        
        result = agent.analyze("AAPL", technical_data)
        
        assert "risk_level" in result
        assert "suggested_position_size" in result
        # High RSI should increase volatility/risk
        
    @patch('src.agents.decision_agent.OpenAI')
    def test_decision_agent(self, mock_openai):
        """Test decision orchestrator."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Mock LLM decision
        decision_json = '{"recommendation": "BUY", "confidence": 0.85, "reasoning": "Strong signals", "primary_driver": "Technical"}'
        mock_client.chat.completions.create.return_value.choices[0].message.content = decision_json
        
        agent = DecisionAgent()
        result = agent.decide(
            "AAPL",
            {"sentiment_score": 0.8},
            {"technical_score": 0.7},
            {"risk_level": "LOW"}
        )
        
        assert result["recommendation"] == "BUY"
        assert result["confidence"] == 0.85
