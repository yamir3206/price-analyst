"""Add durable retail and wholesale snapshot-cache columns and table.

Revision ID: 0002_durable_snapshot_cache
Revises: 0001_initial_persistence
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_durable_snapshot_cache"
down_revision: str | None = "0001_initial_persistence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "search_snapshots",
        sa.Column("cache_key", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "search_snapshots",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_search_snapshots_cache_key",
        "search_snapshots",
        ["cache_key"],
        unique=True,
    )
    op.create_table(
        "wholesale_snapshots",
        sa.Column("search_id", sa.String(length=36), nullable=False),
        sa.Column("normalized_query", sa.String(length=500), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cache_key", sa.String(length=128), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("search_id"),
    )
    op.create_index(
        "ix_wholesale_snapshots_normalized_query",
        "wholesale_snapshots",
        ["normalized_query"],
    )
    op.create_index(
        "ix_wholesale_snapshots_cache_key",
        "wholesale_snapshots",
        ["cache_key"],
        unique=True,
    )
    op.create_index(
        "ix_wholesale_snapshots_collected_at",
        "wholesale_snapshots",
        ["collected_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_wholesale_snapshots_collected_at", table_name="wholesale_snapshots")
    op.drop_index("ix_wholesale_snapshots_cache_key", table_name="wholesale_snapshots")
    op.drop_index("ix_wholesale_snapshots_normalized_query", table_name="wholesale_snapshots")
    op.drop_table("wholesale_snapshots")
    op.drop_index("ix_search_snapshots_cache_key", table_name="search_snapshots")
    op.drop_column("search_snapshots", "expires_at")
    op.drop_column("search_snapshots", "cache_key")
