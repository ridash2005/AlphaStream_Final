"""
Sentiment Analysis Agent for financial news.

Analyzes articles to determine market sentiment using LLM.
"""

import json
import logging
from typing import Any

from openai import OpenAI

from src.config import get_settings

logger = logging.getLogger(__name__)


class SentimentAgent:
    """
    Analyzes market sentiment from news articles.
    
    Uses OpenRouter-compatible API for LLM inference.
    
    Output:
        - sentiment_score: float from -1.0 (bearish) to +1.0 (bullish)
        - sentiment_label: BEARISH, NEUTRAL, or BULLISH
        - key_factors: list of reasons driving the sentiment
        - confidence: float from 0.0 to 1.0
    """

    SENTIMENT_PROMPT = """Analyze the sentiment of the following financial news articles about stocks.

Articles:
{articles}

Task: Determine the overall market sentiment for trading decisions.

Consider:
1. Company announcements (earnings, products, leadership)
2. Regulatory or legal developments
3. Market analyst commentary
4. Competitive positioning
5. Industry trends

Output ONLY a valid JSON object (no markdown, no explanation):
{{
    "sentiment_score": <float between -1.0 and 1.0>,
    "sentiment_label": "<BEARISH|NEUTRAL|BULLISH>",
    "key_factors": ["<factor1>", "<factor2>"],
    "confidence": <float 0.0-1.0>
}}"""

    def __init__(self, model: str | None = None):
        settings = get_settings()
        self.model = model or settings.llm_model
        self.client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )

    def analyze(self, articles: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Analyze sentiment from retrieved articles.

        Args:
            articles: List of article dicts with 'text', 'title', 'source'

        Returns:
            Dict with sentiment_score, sentiment_label, key_factors, confidence
        """
        if not articles:
            return self._neutral_response("No articles provided")

        # Format articles for prompt
        articles_text = self._format_articles(articles)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": self.SENTIMENT_PROMPT.format(articles=articles_text),
                    }
                ],
                temperature=0,
                max_tokens=500,
            )

            content = response.choices[0].message.content
            if not content:
                return self._neutral_response("Empty response from LLM")

            # Parse JSON response
            sentiment_data = json.loads(content.strip())

            # Validate and clamp values
            sentiment_data["sentiment_score"] = max(
                -1.0, min(1.0, float(sentiment_data.get("sentiment_score", 0)))
            )
            sentiment_data["confidence"] = max(
                0.0, min(1.0, float(sentiment_data.get("confidence", 0.5)))
            )

            if sentiment_data.get("sentiment_label") not in ["BEARISH", "NEUTRAL", "BULLISH"]:
                sentiment_data["sentiment_label"] = self._score_to_label(
                    sentiment_data["sentiment_score"]
                )

            logger.info(
                f"Sentiment: {sentiment_data['sentiment_label']} "
                f"(score: {sentiment_data['sentiment_score']:.2f})"
            )

            return sentiment_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return self._neutral_response("Failed to parse response")
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return self._neutral_response(str(e))

    def _format_articles(self, articles: list[dict[str, Any]]) -> str:
        """Format articles for the prompt."""
        parts = []
        for i, article in enumerate(articles[:10], 1):  # Limit to 10 articles
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

    def _score_to_label(self, score: float) -> str:
        """Convert sentiment score to label."""
        if score > 0.3:
            return "BULLISH"
        elif score < -0.3:
            return "BEARISH"
        return "NEUTRAL"
