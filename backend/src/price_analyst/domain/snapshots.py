"""Search snapshot contracts returned by the API and persisted for reuse."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from price_analyst.domain.ai_analysis import AIAnalysisEnvelope
from price_analyst.domain.enums import CollectionStatus
from price_analyst.domain.local_analysis import LocalAnalysis
from price_analyst.domain.offers import Offer
from price_analyst.domain.queries import NormalizedQuery
from price_analyst.domain.source_health import SourceStatus
from price_analyst.domain.statistics import PriceStatistics


class SearchSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    search_id: UUID = Field(default_factory=uuid4)
    query: NormalizedQuery
    offers: list[Offer] = Field(default_factory=list)
    statistics: PriceStatistics | None = None
    source_statuses: list[SourceStatus] = Field(default_factory=list)
    collection_status: CollectionStatus
    collected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    stale: bool = False
    local_analysis: LocalAnalysis = Field(default_factory=LocalAnalysis)
    ai_analysis: AIAnalysisEnvelope = Field(default_factory=AIAnalysisEnvelope)
