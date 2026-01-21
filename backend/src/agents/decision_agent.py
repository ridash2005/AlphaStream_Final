"""
Decision Agent (Orchestrator).
Refactored to use LangChain.
"""

import json
import logging
from typing import Any, Dict

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.config import get_settings

logger = logging.getLogger(__name__)


class DecisionOutput(BaseModel):
    """Schema for decision output."""
    recommendation: str = Field(description="BUY, SELL, or HOLD")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(description="Concise explanation of the decision")
    primary_driver: str = Field(description="Sentiment, Technical, Risk, or Mixed")


class DecisionAgent:
    """
    Final decision maker using LangChain.
    """

    def __init__(self, model: str | None = None):
        settings = get_settings()
        self.model = model or settings.llm_model
        
        self.llm = ChatOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            model=self.model,
            temperature=0.1,
            max_retries=5,
            request_timeout=60,
        )
        
        self.parser = PydanticOutputParser(pydantic_object=DecisionOutput)
        
        self.prompt = PromptTemplate(
            template="""You are a senior portfolio manager making a final trading decision for {ticker}.

Synthesize the following analyses:

1. MARKET SENTIMENT:
{sentiment_data}

2. TECHNICAL ANALYSIS:
{technical_data}

3. RISK ASSESSMENT:
{risk_data}

Make a definitive recommendation (BUY, SELL, or HOLD).

{format_instructions}
""",
            input_variables=["ticker", "sentiment_data", "technical_data", "risk_data"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )
        
        self.chain = self.prompt | self.llm | self.parser

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
            # Invoke chain
            result = self.chain.invoke({
                "ticker": ticker,
                "sentiment_data": json.dumps(sentiment_data),
                "technical_data": json.dumps(technical_data),
                "risk_data": json.dumps(risk_data)
            })
            
            return result.model_dump()
            
        except Exception as e:
            logger.error(f"Decision agent error: {e}")
            return self._heuristic_fallback(sentiment_data, technical_data, risk_data)

    def _heuristic_fallback(self, sentiment, technical, risk) -> Dict[str, Any]:
        """Simple rule-based fallback."""
        sent_score = sentiment.get("sentiment_score", 0)
        tech_score = technical.get("technical_score", 0)
        
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
