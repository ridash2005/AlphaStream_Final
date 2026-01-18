"""Configuration management for AlphaStream Live AI."""

from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenRouter API
    openrouter_api_key: str = Field(..., alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL"
    )

    # News APIs
    newsapi_key: str = Field(..., alias="NEWS_API_KEY")
    
    # Additional News Sources (optional - for fallback)
    finnhub_api_key: str = Field(default="", alias="FINNHUB_API_KEY")
    alphavantage_api_key: str = Field(default="", alias="ALPHAVANTAGE_API_KEY")
    mediastack_api_key: str = Field(default="", alias="MEDIASTACK_API_KEY")

    # System Configuration
    log_level: str = Field(default="info", alias="LOG_LEVEL")
    refresh_interval: int = Field(default=30, alias="REFRESH_INTERVAL")

    # Model selection
    llm_model: str = Field(
        default="anthropic/claude-3.5-sonnet", alias="LLM_MODEL"
    )
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", alias="EMBEDDING_MODEL"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
