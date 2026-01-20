"""
Sentiment Analysis Agent for financial news.
Refactored to use LangChain.
"""

import logging
from typing import Any

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.config import get_settings

logger = logging.getLogger(__name__)


class SentimentOutput(BaseModel):
    """Schema for sentiment output."""
    sentiment_score: float = Field(description="float between -1.0 (bearish) and 1.0 (bullish)")
    sentiment_label: str = Field(description="BEARISH, NEUTRAL, or BULLISH")
    key_factors: list[str] = Field(description="List of key factors driving the sentiment")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")


class SentimentAgent:
    """
    Analyzes market sentiment using LangChain.
    """

    def __init__(self, model: str | None = None):
        settings = get_settings()
        self.model = model or settings.llm_model
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            model=self.model,
            temperature=0,
        )
        
        # Initialize Output Parser
        self.parser = PydanticOutputParser(pydantic_object=SentimentOutput)
        
        # Initialize Prompt
        self.prompt = PromptTemplate(
            template="""Analyze the sentiment of the following financial news articles about stocks.

Articles:
{articles}

Task: Determine the overall market sentiment for trading decisions.

Consider:
1. Company announcements
2. Regulatory developments
3. Analyst commentary
4. Industry trends

{format_instructions}

Return ONLY the JSON object.
""",
            input_variables=["articles"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )
        
        # Create Chain
        self.chain = self.prompt | self.llm | self.parser

    def analyze(self, articles: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Analyze sentiment from retrieved articles.
        """
        logger.info(f"📊 Sentiment Agent: Analyzing {len(articles)} articles")
        
        if not articles:
            logger.warning("📊 Sentiment Agent: No articles provided, returning neutral")
            return self._neutral_response("No articles provided")

        articles_text = self._format_articles(articles)
        logger.debug(f"📊 Formatted articles text (first 500 chars): {articles_text[:500]}")

        try:
            # Invoke chain
            result = self.chain.invoke({"articles": articles_text})
            
            # Convert Pydantic model to dict
            result_dict = result.model_dump()
            logger.info(f"📊 Sentiment Result: {result_dict.get('sentiment_label')} "
                       f"(score: {result_dict.get('sentiment_score')}, "
                       f"confidence: {result_dict.get('confidence')})")
            return result_dict

        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return self._neutral_response(f"Agent error: {str(e)}")

    def _format_articles(self, articles: list[dict[str, Any]]) -> str:
        """Format articles for the prompt."""
        parts = []
        for i, article in enumerate(articles[:10], 1):
            title = article.get("title", "Unknown")
            source = article.get("source", "Unknown")
            text = article.get("text", article.get("content", ""))[:500]
            parts.append(f"[{i}] {title} ({source})\n{text}")
        return "\n\n".join(parts)

    def _neutral_response(self, reason: str) -> dict[str, Any]:
        """Return a neutral sentiment response."""
        return {
            "sentiment_score": 0.0,
            "sentiment_label": "NEUTRAL",
            "key_factors": [reason],
            "confidence": 0.0,
        }
