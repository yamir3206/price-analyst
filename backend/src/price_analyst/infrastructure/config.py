"""Environment-backed application configuration."""

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Price Analyst API"
    environment: Literal["development", "test", "staging", "production"] = "development"
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    database_url: str = "sqlite:///./price_analyst.db"
    cors_origins: list[str] = ["*"]

    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.0-flash"
    max_gemini_input_tokens: int = Field(default=4000, ge=256)
    max_gemini_output_tokens: int = Field(default=1000, ge=128)
    max_offers_to_analyze: int = Field(default=30, ge=1)
    gemini_timeout_seconds: float = Field(default=20.0, gt=0)
    analysis_version: str = "1"

    source_timeout_seconds: float = Field(default=10.0, gt=0)
    max_search_candidates: int = Field(default=100, ge=1)
    max_detail_candidates: int = Field(default=8, ge=1)
    source_concurrency: int = Field(default=2, ge=1)
    snapshot_cache_ttl_seconds: int = Field(default=300, ge=0)

    torob_enabled: bool = False
    torob_base_url: str = "https://torob.com"

    model_config = SettingsConfigDict(
        env_prefix="PRICE_ANALYST_",
        env_file=".env",
        extra="ignore",
    )

    @property
    def gemini_configured(self) -> bool:
        return self.gemini_api_key is not None and bool(self.gemini_api_key.get_secret_value())
