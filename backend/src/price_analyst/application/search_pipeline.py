"""Phase 1 search orchestration boundary.

Live adapters are intentionally absent in this phase. The pipeline still
returns a truthful typed snapshot so clients can be developed against the
real API contract without pretending that data was collected.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from price_analyst.collectors.registry import AdapterRegistry
from price_analyst.domain.enums import CollectionStatus, Marketplace, SourceState
from price_analyst.domain.snapshots import SearchSnapshot
from price_analyst.domain.source_health import SourceStatus
from price_analyst.normalization.query_normalizer import normalize_query

_INITIAL_MARKETPLACES = (
    Marketplace.TOROB,
    Marketplace.BASALAM,
    Marketplace.DIGIKALA,
    Marketplace.DIVAR,
)


class SearchPipeline:
    """Application service coordinating source adapters and later analysis."""

    def __init__(self, registry: AdapterRegistry) -> None:
        self._registry = registry

    async def run(self, query_text: str, *, refresh: bool = False) -> SearchSnapshot:
        del refresh  # Refresh policy is introduced with persistent snapshots.
        query = normalize_query(query_text)
        now = datetime.now(UTC)
        statuses: list[SourceStatus] = []
        for source in _INITIAL_MARKETPLACES:
            configured = self._registry.get(source) is not None
            statuses.append(
                SourceStatus(
                    source=source,
                    state=SourceState.READY if configured else SourceState.NOT_CONFIGURED,
                    adapter_configured=configured,
                    last_failure=None,
                    error_code=None if configured else "adapter_not_configured",
                    error_message=(
                        None if configured else "This marketplace adapter is not enabled yet."
                    ),
                )
            )

        configured_count = sum(status.adapter_configured for status in statuses)
        collection_status = (
            CollectionStatus.NO_SOURCES_CONFIGURED
            if configured_count == 0
            else CollectionStatus.PARTIAL
        )
        return SearchSnapshot(
            search_id=uuid4(),
            query=query,
            offers=[],
            statistics=None,
            source_statuses=statuses,
            collection_status=collection_status,
            collected_at=now,
        )
