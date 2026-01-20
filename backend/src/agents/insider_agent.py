"""
Insider Trading Agent - Analyzes SEC Form 4 filings.

Extracts insider trading signals and calculates net insider sentiment.
Uses LLM for complex parsing and summarization when needed.
"""

import logging
from typing import Any

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.config import get_settings
from src.connectors.sec_connector import get_sec_connector

logger = logging.getLogger(__name__)


class InsiderAnalysis(BaseModel):
    """Schema for insider trading analysis output."""
    insider_score: float = Field(description="Score from -1.0 (heavy selling) to 1.0 (heavy buying)")
    sentiment: str = Field(description="BEARISH, NEUTRAL, or BULLISH based on insider activity")
    total_buy_value: float = Field(description="Total value of insider purchases in USD")
    total_sell_value: float = Field(description="Total value of insider sales in USD")
    key_transactions: list[str] = Field(description="List of notable insider transactions")
    summary: str = Field(description="Brief summary of insider activity patterns")


class InsiderAgent:
    """
    Analyzes insider trading activity from SEC Form 4 filings.
    
    Uses edgartools for data and LLM for complex analysis.
    """
    
    def __init__(self, model: str | None = None):
        settings = get_settings()
        self.model = model or settings.llm_model
        self.sec_connector = get_sec_connector()
        
        # Initialize LLM for complex parsing
        self.llm = ChatOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            model=self.model,
            temperature=0,
        )
        
        self.parser = PydanticOutputParser(pydantic_object=InsiderAnalysis)
        
        self.prompt = PromptTemplate(
            template="""Analyze the following insider trading data for {ticker}.

Insider Transactions (last 24-48 hours):
{transactions}

Consider:
1. Net buying vs selling activity
2. Who is trading (CEO, CFO, Directors are more significant)
3. Size of transactions relative to typical activity
4. Timing patterns (clustered buying/selling)

A score of 1.0 means heavy insider buying (very bullish signal).
A score of -1.0 means heavy insider selling (bearish signal).
A score of 0.0 means neutral or no significant activity.

{format_instructions}
""",
            input_variables=["ticker", "transactions"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )
        
        self.chain = self.prompt | self.llm | self.parser
    
    def analyze(self, ticker: str, days: int = 1) -> dict[str, Any]:
        """
        Analyze insider trading activity for a ticker.
        
        Args:
            ticker: Stock symbol
            days: Days to look back (default: 1)
            
        Returns:
            Dict with insider_score, sentiment, transactions summary
        """
        try:
            # Fetch insider trades from SEC
            logger.info(f"🔍 Insider Agent: Fetching trades for {ticker} (last {days} days)")
            transactions = self.sec_connector.get_insider_trades(ticker, days=days)
            
            logger.info(f"🔍 Insider Agent: Found {len(transactions)} transactions")
            
            if not transactions:
                logger.info(f"🔍 Insider Agent: No recent transactions found, returning neutral")
                return self._neutral_response("No recent insider transactions found")
            
            # Check if we need LLM fallback
            if transactions[0].get("insider_name") == "LLM_FALLBACK_REQUIRED":
                return self._llm_web_analysis(ticker)
            
            # Format transactions for LLM analysis
            trans_text = self._format_transactions(transactions)
            
            # Use LLM to analyze patterns
            result = self.chain.invoke({
                "ticker": ticker,
                "transactions": trans_text
            })
            
            return result.model_dump()
            
        except Exception as e:
            logger.error(f"Insider analysis error for {ticker}: {e}")
            return self._neutral_response(f"Analysis error: {str(e)}")
    
    def _format_transactions(self, transactions: list[dict]) -> str:
        """Format transaction data for LLM prompt."""
        if not transactions:
            return "No transactions found."
        
        parts = []
        for i, trans in enumerate(transactions[:15], 1):  # Limit to 15
            parts.append(
                f"[{i}] {trans.get('insider_name', 'Unknown')} - "
                f"{trans.get('transaction_type', 'Unknown')} - "
                f"{trans.get('shares', 0)} shares @ ${trans.get('price', 0):.2f} - "
                f"Filed: {trans.get('filing_date', 'Unknown')}"
            )
        return "\n".join(parts)
    
    def _llm_web_analysis(self, ticker: str) -> dict[str, Any]:
        """
        Use LLM to analyze insider trading when edgartools unavailable.
        
        The LLM will use its knowledge to provide general guidance.
        """
        try:
            prompt = f"""Based on your knowledge, provide a general analysis of typical 
insider trading patterns for {ticker}. 

Note: This is a fallback when real-time SEC data is unavailable.
Provide conservative estimates and clearly indicate this is based on general knowledge.

Return a JSON with:
- insider_score: float (-1 to 1), be conservative (use 0 to 0.3 range)
- sentiment: "NEUTRAL" (since we don't have real data)
- total_buy_value: 0
- total_sell_value: 0
- key_transactions: ["No real-time data available - using LLM fallback"]
- summary: Brief note about typical insider activity patterns for this company
"""
            response = self.llm.invoke(prompt)
            
            # Parse response manually since it's freeform
            return {
                "insider_score": 0.0,
                "sentiment": "NEUTRAL",
                "total_buy_value": 0,
                "total_sell_value": 0,
                "key_transactions": ["LLM fallback - no real-time SEC data"],
                "summary": response.content[:500] if hasattr(response, 'content') else "Fallback analysis"
            }
            
        except Exception as e:
            logger.error(f"LLM fallback error: {e}")
            return self._neutral_response("LLM fallback failed")
    
    def _neutral_response(self, reason: str) -> dict[str, Any]:
        """Return neutral response when analysis fails."""
        return {
            "insider_score": 0.0,
            "sentiment": "NEUTRAL",
            "total_buy_value": 0,
            "total_sell_value": 0,
            "key_transactions": [reason],
            "summary": reason
        }
