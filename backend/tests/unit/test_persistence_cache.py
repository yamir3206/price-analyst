from datetime import UTC, datetime

import pytest

from price_analyst.cache.wholesale import InMemoryWholesaleSnapshotCache
from price_analyst.domain.enums import CollectionStatus
from price_analyst.domain.queries import NormalizedQuery
from price_analyst.domain.snapshots import SearchSnapshot
from price_analyst.domain.wholesale import WholesaleSnapshot
from price_analyst.persistence.cache import (
    SqlAlchemySnapshotCache,
    SqlAlchemyWholesaleSnapshotCache,
)
from price_analyst.persistence.database import (
    Base,
    create_database_engine,
    create_session_factory,
)


def query() -> NormalizedQuery:
    return NormalizedQuery(
        original="Samsung S24",
        normalized_text="samsung s24",
        variants=["samsung s24"],
    )


@pytest.mark.asyncio
async def test_sqlalchemy_snapshot_cache_round_trips_and_expires(tmp_path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'cache.db'}")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    cache = SqlAlchemySnapshotCache(factory, max_entries=2)
    snapshot = SearchSnapshot(
        query=query(),
        collection_status=CollectionStatus.NO_SOURCES_CONFIGURED,
    )

    await cache.put("search-key", snapshot, ttl_seconds=60)
    stored = await cache.get("search-key")
    assert stored is not None
    assert stored.search_id == snapshot.search_id

    await cache.put("expired-key", snapshot, ttl_seconds=0)
    assert await cache.get("expired-key") is None
    engine.dispose()


@pytest.mark.asyncio
async def test_sqlalchemy_wholesale_cache_round_trips(tmp_path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'wholesale.db'}")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    cache = SqlAlchemyWholesaleSnapshotCache(factory, max_entries=2)
    snapshot = WholesaleSnapshot(
        query=query(),
        collection_status=CollectionStatus.NO_SOURCES_CONFIGURED,
        collected_at=datetime.now(UTC),
    )

    await cache.put("wholesale-key", snapshot, ttl_seconds=60)
    stored = await cache.get("wholesale-key")
    assert stored is not None
    assert stored.search_id == snapshot.search_id
    engine.dispose()


@pytest.mark.asyncio
async def test_in_memory_wholesale_cache_expires() -> None:
    cache = InMemoryWholesaleSnapshotCache()
    snapshot = WholesaleSnapshot(
        query=query(),
        collection_status=CollectionStatus.NO_SOURCES_CONFIGURED,
    )

    await cache.put("key", snapshot, ttl_seconds=0)
    assert await cache.get("key") is None
