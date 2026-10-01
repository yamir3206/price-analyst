"""Gemini input and strictly validated output contracts."""

from pydantic import BaseModel, ConfigDict, Field

from price_analyst.domain.enums import AIAnalysisStatus, Currency, Marketplace
from price_analyst.domain.statistics import PriceStatistics


class CompactOffer(BaseModel):
    """Token-conscious offer representation; never contains raw HTML or URLs."""

    model_config = ConfigDict(extra="forbid")

    offer_id: str = Field(min_length=1)
    source: Marketplace
    title: str | None = Field(default=None, max_length=300)
    price: int | None = Field(default=None, ge=0)
    currency: Currency | None = None
    seller: str | None = Field(default=None, max_length=200)
    condition: str | None = None
    availability: str | None = None
    classification: str | None = None
    match_score: float | None = Field(default=None, ge=0, le=1)


class CompactAnalysisDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "2"
    product: str = Field(min_length=1, max_length=300)
    offers: list[CompactOffer] = Field(default_factory=list, max_length=100)
    statistics: PriceStatistics | None = None
    statistics_by_currency: list[PriceStatistics] = Field(default_factory=list, max_length=10)
    stale: bool = False
    dataset_hash: str | None = None


class AIAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    summary: str = Field(default="", max_length=4000)
    market_assessment: str = Field(default="", max_length=4000)
    cheap_offers: list[str] = Field(default_factory=list, max_length=20)
    expensive_offers: list[str] = Field(default_factory=list, max_length=20)
    potential_opportunities: list[str] = Field(default_factory=list, max_length=20)
    risks: list[str] = Field(default_factory=list, max_length=20)
    missing_information: list[str] = Field(default_factory=list, max_length=20)
    facts: list[str] = Field(default_factory=list, max_length=30)
    inferences: list[str] = Field(default_factory=list, max_length=30)
    uncertainties: list[str] = Field(default_factory=list, max_length=30)
    confidence: float = Field(ge=0, le=1)


class AIAnalysisEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: AIAnalysisStatus = AIAnalysisStatus.NOT_REQUESTED
    result: AIAnalysis | None = None
    dataset_hash: str | None = None
    prompt_version: str | None = None
    model: str | None = None
    error_code: str | None = None
    error_message: str | None = None
