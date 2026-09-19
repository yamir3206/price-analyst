"""Application-layer ports for cache and optional AI services."""

from __future__ import annotations

from typing import Protocol

from price_analyst.domain.ai_analysis import AIAnalysis, CompactAnalysisDataset
from price_analyst.domain.snapshots import SearchSnapshot


class SnapshotCache(Protocol):
    async def get(self, key: str) -> SearchSnapshot | None:
        ...

    async def put(self, key: str, value: SearchSnapshot, ttl_seconds: int) -> None:
        ...


class AIAnalysisCache(Protocol):
    async def get(self, key: str) -> AIAnalysis | None:
        ...

    async def put(self, key: str, value: AIAnalysis, ttl_seconds: int) -> None:
        ...


class GeminiClient(Protocol):
    enabled: bool

    async def analyze(self, dataset: CompactAnalysisDataset) -> AIAnalysis:
        ...
