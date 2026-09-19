"""Offer and candidate records shared across adapters and the API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from price_analyst.domain.enums import Availability, Marketplace, OfferCondition
from price_analyst.domain.money import Money


class SearchCandidate(BaseModel):
    """Small record returned by the first, low-bandwidth search stage."""

    model_config = ConfigDict(extra="forbid")

    source: Marketplace
    source_offer_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    price: Money | None = None
    seller: str | None = None
    availability: Availability = Availability.UNKNOWN
    condition: OfferCondition = OfferCondition.UNKNOWN
    brand: str | None = None
    model: str | None = None
    capacity: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class Offer(BaseModel):
    """Normalized offer retained in the full deterministic dataset."""

    model_config = ConfigDict(extra="forbid")

    offer_id: str = Field(min_length=1)
    source: Marketplace
    source_offer_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    normalized_title: str = Field(min_length=1)
    price: Money | None = None
    original_price: Money | None = None
    seller: str | None = None
    product_url: str = Field(min_length=1)
    image_url: str | None = None
    availability: Availability = Availability.UNKNOWN
    condition: OfferCondition = OfferCondition.UNKNOWN
    brand: str | None = None
    model: str | None = None
    capacity: str | None = None
    specifications: dict[str, str] = Field(default_factory=dict)
    shipping: Money | None = None
    shipping_information: str | None = None
    observed_at: datetime
    details_fetched: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)
