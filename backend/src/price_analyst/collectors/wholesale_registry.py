"""Explicit registry for wholesale adapters."""

from __future__ import annotations

from price_analyst.collectors.wholesale import WholesaleAdapter


class WholesaleAdapterRegistry:
    """Keep wholesale source discovery separate from retail marketplaces."""

    def __init__(self, adapters: list[WholesaleAdapter] | None = None) -> None:
        self._adapters: dict[str, WholesaleAdapter] = {}
        for adapter in adapters or []:
            self.register(adapter)

    def register(self, adapter: WholesaleAdapter) -> None:
        self._adapters[adapter.source] = adapter

    def get(self, source: str) -> WholesaleAdapter | None:
        return self._adapters.get(source)

    def all(self) -> tuple[WholesaleAdapter, ...]:
        return tuple(self._adapters.values())

    def sources(self) -> tuple[str, ...]:
        return tuple(self._adapters.keys())
