"""Gemini input and validated output contracts."""

from pydantic import BaseModel, ConfigDict, Field

from price_analyst.domain.enums import AIAnalysisStatus, Marketplace
from price_analyst.domain.statistics import PriceStatistics


class CompactOffer(BaseModel):
    """Token-conscious offer representation; never contains raw HTML."""

    model_config = ConfigDict(extra="forbid")

    offer_id: str = Field(min_length=1)
    source: Marketplace
    price: int | None = Field(default=None, ge=0)
    seller: str | None = None
    condition: str | None = None
    availability: str | None = None


class CompactAnalysisDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1"
    product: str = Field(min_length=1)
    offers: list[CompactOffer] = Field(default_factory=list)
    statistics: PriceStatistics | None = None
    dataset_hash: str | None = None


class AIAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = ""
    market_assessment: str = ""
    cheap_offers: list[str] = Field(default_factory=list)
    expensive_offers: list[str] = Field(default_factory=list)
    potential_opportunities: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    inferences: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class AIAnalysisEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: AIAnalysisStatus = AIAnalysisStatus.NOT_REQUESTED
    result: AIAnalysis | None = None
    error_code: str | None = None
    error_message: str | None = None
