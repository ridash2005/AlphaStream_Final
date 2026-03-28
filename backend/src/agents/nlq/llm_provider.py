"""
LLM provider for AlphaStream India NLQ agent.

Uses Google Vertex AI (Gemini) — same as MediaFlowAI.
Env vars:
  GOOGLE_APPLICATION_CREDENTIALS  path to GCP service account JSON
  GCP_PROJECT_ID                  agrowise-192e3
  GCP_REGION                      us-central1
  VERTEX_MODEL                    gemini-2.0-flash
"""
from __future__ import annotations

import os
import warnings
from functools import lru_cache

from dotenv import load_dotenv
load_dotenv()

warnings.filterwarnings("ignore", message="Use.*ChatGoogleGenerativeAI", category=DeprecationWarning)

GCP_PROJECT = os.environ.get("GCP_PROJECT_ID", "agrowise-192e3")
GCP_REGION = os.environ.get("GCP_REGION", "us-central1")
VERTEX_MODEL = os.environ.get("VERTEX_MODEL", "gemini-2.0-flash")


@lru_cache(maxsize=4)
def get_llm(temperature: float = 0.0, max_tokens: int = 1024):
    """Return a cached ChatVertexAI instance."""
    from langchain_google_vertexai import ChatVertexAI
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return ChatVertexAI(
            model_name=VERTEX_MODEL,
            project=GCP_PROJECT,
            location=GCP_REGION,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )


def complete(
    prompt: str,
    system: str = "",
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> str:
    """Single-turn completion. Returns response text."""
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = get_llm(temperature=temperature, max_tokens=max_tokens)
    messages = []
    if system:
        messages.append(SystemMessage(content=system))
    messages.append(HumanMessage(content=prompt))
    return llm.invoke(messages).content
