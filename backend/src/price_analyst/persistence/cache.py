"""SQLite/PostgreSQL-compatible durable snapshot caches."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from price_analyst.domain.snapshots import SearchSnapshot
from price_analyst.domain.wholesale import WholesaleSnapshot
from price_analyst.persistence.models import StoredSearch, StoredWholesaleSearch


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class SqlAlchemySnapshotCache:
    """Durable TTL cache for deterministic retail snapshots."""

    def __init__(self, factory: sessionmaker[Session], *, max_entries: int = 1000) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be at least one")
        self._factory = factory
        self._max_entries = max_entries

    async def get(self, key: str) -> SearchSnapshot | None:
        return await asyncio.to_thread(self._get, key)

    async def put(self, key: str, value: SearchSnapshot, ttl_seconds: int) -> None:
        await asyncio.to_thread(self._put, key, value, ttl_seconds)

    def _get(self, key: str) -> SearchSnapshot | None:
        with self._factory() as session:
            row = session.scalar(
                select(StoredSearch).where(StoredSearch.cache_key == key)
            )
            if row is None:
                return None
            if row.expires_at is not None and _aware(row.expires_at) <= datetime.now(UTC):
                session.delete(row)
                session.commit()
                return None
            try:
                return SearchSnapshot.model_validate(row.payload)
            except ValueError:
                session.delete(row)
                session.commit()
                return None

    def _put(self, key: str, value: SearchSnapshot, ttl_seconds: int) -> None:
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=max(0, ttl_seconds))
        payload = value.model_dump(mode="json")
        with self._factory() as session:
            row = session.scalar(
                select(StoredSearch).where(StoredSearch.cache_key == key)
            )
            if row is None:
                row = session.get(StoredSearch, str(value.search_id))
            if row is None:
                row = StoredSearch(
                    search_id=str(value.search_id),
                    normalized_query=value.query.normalized_text,
                    payload=payload,
                    dataset_hash=None,
                    collected_at=value.collected_at,
                    cache_key=key,
                    expires_at=expires_at,
                )
                session.add(row)
            else:
                row.search_id = str(value.search_id)
                row.normalized_query = value.query.normalized_text
                row.payload = payload
                row.collected_at = value.collected_at
                row.expires_at = expires_at
            session.execute(
                delete(StoredSearch).where(
                    StoredSearch.expires_at.is_not(None),
                    StoredSearch.expires_at <= now,
                )
            )
            self._trim(session)
            session.commit()

    def _trim(self, session: Session) -> None:
        rows = session.scalars(
            select(StoredSearch)
            .where(StoredSearch.cache_key.is_not(None))
            .order_by(StoredSearch.collected_at.desc())
            .offset(self._max_entries)
        ).all()
        for row in rows:
            session.delete(row)


class SqlAlchemyWholesaleSnapshotCache:
    """Durable TTL cache for wholesale snapshots."""

    def __init__(self, factory: sessionmaker[Session], *, max_entries: int = 500) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be at least one")
        self._factory = factory
        self._max_entries = max_entries

    async def get(self, key: str) -> WholesaleSnapshot | None:
        return await asyncio.to_thread(self._get, key)

    async def put(self, key: str, value: WholesaleSnapshot, ttl_seconds: int) -> None:
        await asyncio.to_thread(self._put, key, value, ttl_seconds)

    def _get(self, key: str) -> WholesaleSnapshot | None:
        with self._factory() as session:
            row = session.scalar(
                select(StoredWholesaleSearch).where(StoredWholesaleSearch.cache_key == key)
            )
            if row is None:
                return None
            if row.expires_at is not None and _aware(row.expires_at) <= datetime.now(UTC):
                session.delete(row)
                session.commit()
                return None
            try:
                return WholesaleSnapshot.model_validate(row.payload)
            except ValueError:
                session.delete(row)
                session.commit()
                return None

    def _put(self, key: str, value: WholesaleSnapshot, ttl_seconds: int) -> None:
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=max(0, ttl_seconds))
        payload = value.model_dump(mode="json")
        with self._factory() as session:
            row = session.scalar(
                select(StoredWholesaleSearch).where(StoredWholesaleSearch.cache_key == key)
            )
            if row is None:
                row = session.get(StoredWholesaleSearch, str(value.search_id))
            if row is None:
                row = StoredWholesaleSearch(
                    search_id=str(value.search_id),
                    normalized_query=value.query.normalized_text,
                    payload=payload,
                    collected_at=value.collected_at,
                    cache_key=key,
                    expires_at=expires_at,
                )
                session.add(row)
            else:
                row.search_id = str(value.search_id)
                row.normalized_query = value.query.normalized_text
                row.payload = payload
                row.collected_at = value.collected_at
                row.expires_at = expires_at
            session.execute(
                delete(StoredWholesaleSearch).where(
                    StoredWholesaleSearch.expires_at.is_not(None),
                    StoredWholesaleSearch.expires_at <= now,
                )
            )
            self._trim(session)
            session.commit()

    def _trim(self, session: Session) -> None:
        rows = session.scalars(
            select(StoredWholesaleSearch)
            .order_by(StoredWholesaleSearch.collected_at.desc())
            .offset(self._max_entries)
        ).all()
        for row in rows:
            session.delete(row)
