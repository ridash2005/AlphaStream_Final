"""
LLM provider for NLQ agent — delegates to central src.llm module.
"""
from src.llm import get_llm, complete

__all__ = ["get_llm", "complete"]
