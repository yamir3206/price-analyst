"""Runtime registry for marketplace adapters."""

from price_analyst.collectors.interfaces import MarketplaceAdapter
from price_analyst.domain.enums import Marketplace


class AdapterRegistry:
    """A small explicit registry keeps source discovery out of the domain."""

    def __init__(self, adapters: list[MarketplaceAdapter] | None = None) -> None:
        self._adapters: dict[Marketplace, MarketplaceAdapter] = {}
        for adapter in adapters or []:
            self.register(adapter)

    def register(self, adapter: MarketplaceAdapter) -> None:
        self._adapters[adapter.source] = adapter

    def get(self, source: Marketplace) -> MarketplaceAdapter | None:
        return self._adapters.get(source)

    def all(self) -> tuple[MarketplaceAdapter, ...]:
        return tuple(self._adapters.values())

    def sources(self) -> tuple[Marketplace, ...]:
        return tuple(self._adapters.keys())
