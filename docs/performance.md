# Performance measurements

Phase 6 keeps deterministic analysis authoritative and measures bounded collection rather than optimizing by dropping data. Retail and wholesale source fan-out use bounded semaphores; candidate/listing counts, detail work, retries, timeouts, and cache entries are all bounded. Source health records response time in milliseconds.

## Durable-cache benchmark

Apply migrations to the target database before running the repeatable read benchmark:

```bash
alembic -c backend/alembic.ini upgrade head
PYTHONPATH=backend/src python backend/scripts/benchmark_snapshot_cache.py \
  --database-url sqlite:///./price_analyst.db --iterations 1000
```

The command prints JSON containing `p50_ms`, `p95_ms`, and `max_ms`. Run it against the same database and deployment configuration when comparing SQLite and PostgreSQL; do not treat a workstation-specific threshold as a correctness requirement. The benchmark seeds one typed deterministic snapshot, reads it repeatedly through the same async cache port used by the application, and fails if the snapshot expires or cannot be reconstructed.

The automated backend suite also covers source concurrency/rate-limiting behavior, partial failures, stale reuse, cache expiry, and durable-cache round trips. Timing assertions intentionally use only broad safety bounds; exact latency depends on the runner, database, network, and configured source limits.
