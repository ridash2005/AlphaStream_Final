"""
Filing Analyst Agent — BSE/NSE corporate filing classification.

Uses LLM to classify filings as material vs routine, extract key facts.
"""
import logging
from typing import Any

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from src.llm import get_llm

logger = logging.getLogger(__name__)


class FilingAnalysis(BaseModel):
    filing_type: str = Field(description="board_meeting, acquisition, debt, expansion, regulatory, routine")
    materiality: str = Field(description="high, medium, or low")
    sentiment: str = Field(description="positive, negative, or neutral")
    key_facts: list[str] = Field(description="Key facts extracted from the filing")
    market_impact: str = Field(description="significant_positive, mild_positive, neutral, mild_negative, significant_negative")
    reasoning: str = Field(description="1-2 sentence explanation of analysis")


class FilingAgent:
    """Analyzes BSE/NSE corporate filings using LLM."""

    def __init__(self):
        self._llm = None
        self.parser = PydanticOutputParser(pydantic_object=FilingAnalysis)
        self.prompt = PromptTemplate(
            template="""You are an Indian market financial analyst specializing in BSE/NSE corporate filings.

Analyze this corporate filing for {company} ({ticker}):

Filing text:
{filing_text}

Classify the filing and extract key information.
Filing types: board_meeting, acquisition, debt, expansion, regulatory, routine
Materiality: high (affects stock price), medium (noteworthy), low (routine)
Market impact: significant_positive, mild_positive, neutral, mild_negative, significant_negative

{format_instructions}
""",
            input_variables=["company", "ticker", "filing_text"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )
        self._chain = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_llm(temperature=0.0)
        return self._llm

    @property
    def chain(self):
        if self._chain is None:
            self._chain = self.prompt | self.llm | self.parser
        return self._chain

    def analyze(self, filing_text: str, ticker: str = "", company: str = "") -> dict[str, Any]:
        """Classify a corporate filing."""
        try:
            result = self.chain.invoke({
                "company": company or ticker,
                "ticker": ticker,
                "filing_text": filing_text[:2000],
            })
            return result.model_dump()
        except Exception as e:
            logger.error(f"Filing analysis error: {e}")
            return {
                "filing_type": "routine",
                "materiality": "low",
                "sentiment": "neutral",
                "key_facts": [f"Analysis failed: {str(e)[:100]}"],
                "market_impact": "neutral",
                "reasoning": "Unable to analyze filing",
            }
