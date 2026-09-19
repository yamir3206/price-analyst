"""Source health and partial-failure contracts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from price_analyst.domain.enums import Marketplace, SourceState


class SourceStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Marketplace
    state: SourceState
    adapter_configured: bool = False
    last_success: datetime | None = None
    last_failure: datetime | None = None
    average_response_time_ms: float | None = Field(default=None, ge=0)
    candidate_count: int = Field(default=0, ge=0)
    offer_count: int = Field(default=0, ge=0)
    failure_count: int = Field(default=0, ge=0)
    temporary_disabled_until: datetime | None = None
    stale_data_available: bool = False
    stale_data_timestamp: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None
