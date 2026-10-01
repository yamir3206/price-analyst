"""Typed outputs of deterministic local offer analysis."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from price_analyst.domain.enums import Currency, Marketplace, PriceClassification
from price_analyst.domain.opportunities import OpportunityResult
from price_analyst.domain.statistics import PriceStatistics


class OfferMatch(BaseModel):
    """Evidence-backed match decision between a query and one offer."""

    model_config = ConfigDict(extra="forbid")

    offer_id: str = Field(min_length=1)
    score: float = Field(ge=0, le=1)
    is_match: bool = False
    matched_fields: list[str] = Field(default_factory=list)
    mismatched_fields: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)


class DeduplicationGroup(BaseModel):
    """Equivalent product offers grouped without deleting source records."""

    model_config = ConfigDict(extra="forbid")

    group_id: str = Field(min_length=1)
    canonical_key: str = Field(min_length=1)
    representative_offer_id: str = Field(min_length=1)
    offer_ids: list[str] = Field(min_length=1)


class OfferClassification(BaseModel):
    """Deterministic relative-price classification for one matched offer."""

    model_config = ConfigDict(extra="forbid")

    offer_id: str = Field(min_length=1)
    classification: PriceClassification = PriceClassification.UNKNOWN
    price: int | None = Field(default=None, ge=0)
    currency: Currency | None = None
    distance_from_median: float | None = None
    relative_to_median: float | None = None


class PriceChartPoint(BaseModel):
    """One deterministic point for a marketplace price chart."""

    model_config = ConfigDict(extra="forbid")

    offer_id: str = Field(min_length=1)
    source: Marketplace
    label: str = Field(min_length=1)
    amount: int = Field(ge=0)
    currency: Currency
    classification: PriceClassification = PriceClassification.UNKNOWN
    group_id: str | None = None


class PriceChart(BaseModel):
    """Price points and reference lines for one explicit currency."""

    model_config = ConfigDict(extra="forbid")

    currency: Currency
    points: list[PriceChartPoint] = Field(default_factory=list)
    p25: float | None = Field(default=None, ge=0)
    median: float | None = Field(default=None, ge=0)
    p75: float | None = Field(default=None, ge=0)


class LocalAnalysis(BaseModel):
    """All deterministic analysis products derived from a full offer set."""

    model_config = ConfigDict(extra="forbid")

    matches: list[OfferMatch] = Field(default_factory=list)
    deduplication_groups: list[DeduplicationGroup] = Field(default_factory=list)
    classifications: list[OfferClassification] = Field(default_factory=list)
    statistics_by_currency: list[PriceStatistics] = Field(default_factory=list)
    price_charts: list[PriceChart] = Field(default_factory=list)
    opportunities: list[OpportunityResult] = Field(default_factory=list)
