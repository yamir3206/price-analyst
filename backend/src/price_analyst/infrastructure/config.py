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
    gemini_cache_ttl_seconds: int = Field(default=3600, ge=0)
    gemini_cache_max_entries: int = Field(default=256, ge=1)
    gemini_concurrency: int = Field(default=2, ge=1)
    gemini_min_interval_seconds: float = Field(default=0.0, ge=0)
    analysis_version: str = "2"

    source_timeout_seconds: float = Field(default=10.0, gt=0)
    max_search_candidates: int = Field(default=100, ge=1)
    max_detail_candidates: int = Field(default=8, ge=1)
    source_concurrency: int = Field(default=2, ge=1)
    source_min_interval_seconds: float = Field(default=0.25, ge=0)
    source_failure_threshold: int = Field(default=3, ge=1)
    source_cooldown_seconds: float = Field(default=300.0, ge=0)
    retry_max_attempts: int = Field(default=3, ge=1, le=5)
    retry_base_delay_seconds: float = Field(default=0.25, ge=0)
    retry_max_delay_seconds: float = Field(default=2.0, ge=0)
    snapshot_cache_ttl_seconds: int = Field(default=300, ge=0)
    analysis_match_threshold: float = Field(default=0.55, ge=0, le=1)
    analysis_max_opportunities: int = Field(default=20, ge=0)

    torob_enabled: bool = False
    torob_base_url: str = "https://torob.com"
    basalam_enabled: bool = False
    basalam_base_url: str = "https://basalam.com"
    digikala_enabled: bool = False
    digikala_base_url: str = "https://www.digikala.com"
    divar_enabled: bool = False
    divar_base_url: str = "https://divar.ir"
    divar_city: str = "tehran"
    divar_category: str = "electronic-devices"

    model_config = SettingsConfigDict(
        env_prefix="PRICE_ANALYST_",
        env_file=".env",
        extra="ignore",
    )

    @property
    def gemini_configured(self) -> bool:
        return self.gemini_api_key is not None and bool(self.gemini_api_key.get_secret_value())
