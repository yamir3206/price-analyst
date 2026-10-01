"""Measure durable snapshot-cache read latency on the configured database."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics
from time import perf_counter

from price_analyst.domain.enums import CollectionStatus
from price_analyst.domain.queries import NormalizedQuery
from price_analyst.domain.snapshots import SearchSnapshot
from price_analyst.normalization.query_normalizer import normalize_query
from price_analyst.persistence.cache import SqlAlchemySnapshotCache
from price_analyst.persistence.database import create_database_engine, create_session_factory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default="sqlite:///./price_analyst.db",
        help="Migrated SQLAlchemy database URL",
    )
    parser.add_argument("--iterations", type=int, default=1000)
    return parser.parse_args()


def percentile(values: list[float], fraction: float) -> float:
    position = max(0, math.ceil(len(values) * fraction) - 1)
    return sorted(values)[position]


async def benchmark(database_url: str, iterations: int) -> dict[str, float | int]:
    if iterations < 1:
        raise ValueError("iterations must be at least one")
    engine = create_database_engine(database_url)
    factory = create_session_factory(engine)
    cache = SqlAlchemySnapshotCache(factory)
    query: NormalizedQuery = normalize_query("Samsung S24")
    snapshot = SearchSnapshot(query=query, collection_status=CollectionStatus.COMPLETE)
    await cache.put("benchmark:search", snapshot, ttl_seconds=3600)

    latencies: list[float] = []
    for _ in range(iterations):
        started = perf_counter()
        stored = await cache.get("benchmark:search")
        latencies.append((perf_counter() - started) * 1000)
        if stored is None:
            raise RuntimeError("benchmark snapshot unexpectedly expired or was not found")

    engine.dispose()
    return {
        "iterations": iterations,
        "p50_ms": round(statistics.median(latencies), 3),
        "p95_ms": round(percentile(latencies, 0.95), 3),
        "max_ms": round(max(latencies), 3),
    }


def main() -> None:
    args = parse_args()
    print(json.dumps(asyncio.run(benchmark(args.database_url, args.iterations)), indent=2))


if __name__ == "__main__":
    main()
