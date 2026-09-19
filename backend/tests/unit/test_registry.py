from dataclasses import dataclass

from price_analyst.collectors.interfaces import SearchContext
from price_analyst.collectors.registry import AdapterRegistry
from price_analyst.domain.enums import Marketplace


@dataclass
class FakeAdapter:
    source: Marketplace

    async def search(self, query, context):
        del query, context
        return []

    async def fetch_details(self, candidate, context):
        del candidate, context
        return None


def test_registry_keeps_adapters_replaceable() -> None:
    adapter = FakeAdapter(Marketplace.TOROB)
    registry = AdapterRegistry([adapter])

    assert registry.get(Marketplace.TOROB) is adapter
    assert registry.sources() == (Marketplace.TOROB,)
    assert SearchContext(request_id="test").max_candidates == 100
