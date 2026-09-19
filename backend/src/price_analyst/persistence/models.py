"""Initial persistence tables; migrations own schema changes."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from price_analyst.persistence.database import Base


class StoredSearch(Base):
    __tablename__ = "search_snapshots"

    search_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    normalized_query: Mapped[str] = mapped_column(String(500), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    dataset_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class SourceHealthRecord(Base):
    __tablename__ = "source_health"

    source: Mapped[str] = mapped_column(String(40), primary_key=True)
    last_success: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    average_response_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    temporary_disabled_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
