"""Wholesale-specific contracts kept separate from retail offer analysis."""

from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from price_analyst.domain.enums import Availability, CollectionStatus, OfferCondition, SourceState
from price_analyst.domain.money import Money
from price_analyst.domain.queries import NormalizedQuery


class WholesaleListing(BaseModel):
    """A public wholesale listing with unknown fields left explicitly empty."""

    model_config = ConfigDict(extra="forbid")

    listing_id: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=500)
    supplier_name: str | None = Field(default=None, max_length=200)
    minimum_order_quantity: int | None = Field(default=None, ge=1)
    unit_price: Money | None = None
    product_url: str | None = Field(default=None, max_length=2000)
    shipping_information: str | None = Field(default=None, max_length=500)
    location: str | None = Field(default=None, max_length=200)
    public_contact: str | None = Field(default=None, max_length=300)
    availability: Availability = Availability.UNKNOWN
    condition: OfferCondition = OfferCondition.UNKNOWN
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("product_url")
    @classmethod
    def validate_product_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("product_url must be an HTTP(S) URL")
        if parsed.username or parsed.password:
            raise ValueError("product_url must not contain credentials")
        return value


class WholesaleSourceStatus(BaseModel):
    """Truthful health information for one independently configured source."""

    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1, max_length=100)
    state: SourceState
    adapter_configured: bool = False
    listing_count: int = Field(default=0, ge=0)
    stale_data_available: bool = False
    stale_data_timestamp: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None


class WholesaleSnapshot(BaseModel):
    """Wholesale results never enter the retail SearchSnapshot pipeline."""

    model_config = ConfigDict(extra="forbid")

    search_id: UUID = Field(default_factory=uuid4)
    query: NormalizedQuery
    listings: list[WholesaleListing] = Field(default_factory=list, max_length=100)
    source_statuses: list[WholesaleSourceStatus] = Field(default_factory=list, max_length=20)
    collection_status: CollectionStatus
    collected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    stale: bool = False
