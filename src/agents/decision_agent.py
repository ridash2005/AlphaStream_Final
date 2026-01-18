"""
Decision Agent (Orchestrator).

Synthesizes inputs from Sentiment, Technical, and Risk agents to make a final trading decision.
"""

import json
import logging
from typing import Any, Dict

from openai import OpenAI

from src.config import get_settings

logger = logging.getLogger(__name__)


class DecisionAgent:
    """
    Final decision maker using LLM reasoning.
    """

    DECISION_PROMPT = """You are a senior portfolio manager making a final trading decision for {ticker}.
    
    Synthesize the following analyses:
    
    1. MARKET SENTIMENT (from News):
    {sentiment_data}
    
    2. TECHNICAL ANALYSIS (from Price/Indicators):
    {technical_data}
    
    3. RISK ASSESSMENT:
    {risk_data}
    
    Make a definitive recommendation (BUY, SELL, or HOLD) with a confidence score and clear reasoning.
    
    Output ONLY a JSON object:
    {{
        "recommendation": "<BUY|SELL|HOLD>",
        "confidence": <float 0.0-1.0>,
        "reasoning": "Concise explanation of why...",
        "primary_driver": "<Sentiment|Technical|Risk|Mixed>"
    }}
    """

    def __init__(self, model: str | None = None):
        settings = get_settings()
        self.model = model or settings.llm_model
        self.client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )

    def decide(
        self,
        ticker: str,
        sentiment_data: Dict[str, Any],
        technical_data: Dict[str, Any],
        risk_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate final trading decision.
        """
        try:
            # Construct prompt context
            prompt = self.DECISION_PROMPT.format(
                ticker=ticker,
                sentiment_data=json.dumps(sentiment_data, indent=2),
                technical_data=json.dumps(technical_data, indent=2),
                risk_data=json.dumps(risk_data, indent=2)
            )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=300,
            )
            
            content = response.choices[0].message.content
            decision = json.loads(content.strip())
            
            # Helper to normalize output
            return decision
            
        except Exception as e:
            logger.error(f"Decision agent error: {e}")
            # Fallback logic if LLM fails
            return self._heuristic_fallback(sentiment_data, technical_data, risk_data)

    def _heuristic_fallback(self, sentiment, technical, risk) -> Dict[str, Any]:
        """Simple rule-based fallback."""
        sent_score = sentiment.get("sentiment_score", 0)
        tech_score = technical.get("technical_score", 0)
        
        # Weighted avg
        final_score = (sent_score * 0.6) + (tech_score * 0.4)
        
        rec = "HOLD"
        if final_score > 0.3:
            rec = "BUY"
        elif final_score < -0.3:
            rec = "SELL"
            
        return {
            "recommendation": rec,
            "confidence": 0.5,
            "reasoning": "Fallback logic used due to agent error.",
            "primary_driver": "Heuristic"
        }
