"""Configuration management for AlphaStream India."""

from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # GCP / Vertex AI
    gcp_project_id: str = Field(default="agrowise-192e3", alias="GCP_PROJECT_ID")
    gcp_region: str = Field(default="us-central1", alias="GCP_REGION")
    vertex_model: str = Field(default="gemini-2.0-flash", alias="VERTEX_MODEL")

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
        default="gemini-2.0-flash", alias="LLM_MODEL"
    )
    embedding_model: str = Field(
        default="text-embedding-005", alias="EMBEDDING_MODEL"
    )

    # Indian Market Configuration
    market_region: str = Field(default="IN", alias="MARKET_REGION")
    nse_base_url: str = Field(
        default="https://www.nseindia.com/api", alias="NSE_BASE_URL"
    )
    bse_base_url: str = Field(
        default="https://api.bseindia.com/BseIndiaAPI/api", alias="BSE_BASE_URL"
    )
    ticker_suffix: str = Field(default=".NS", alias="TICKER_SUFFIX")
    default_index: str = Field(default="NIFTY 50", alias="DEFAULT_INDEX")
    trading_start_hour: int = Field(default=9, alias="TRADING_START_HOUR")
    trading_end_hour: int = Field(default=15, alias="TRADING_END_HOUR")

    # Groww API (pluggable)
    groww_api_token: str = Field(default="", alias="GROWW_API_TOKEN")
    groww_totp_secret: str = Field(default="", alias="GROWW_TOTP_SECRET")

    # DuckDB (NLQ analytics database)
    duckdb_path: str = Field(default="market_analytics.duckdb", alias="DUCKDB_PATH")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
