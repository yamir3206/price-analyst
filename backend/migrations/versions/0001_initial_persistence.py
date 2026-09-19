"""Create initial search and source health tables.

Revision ID: 0001_initial_persistence
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_persistence"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "search_snapshots",
        sa.Column("search_id", sa.String(length=36), nullable=False),
        sa.Column("normalized_query", sa.String(length=500), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("dataset_hash", sa.String(length=64), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("search_id"),
    )
    op.create_index(
        "ix_search_snapshots_normalized_query",
        "search_snapshots",
        ["normalized_query"],
    )
    op.create_index("ix_search_snapshots_dataset_hash", "search_snapshots", ["dataset_hash"])
    op.create_index("ix_search_snapshots_collected_at", "search_snapshots", ["collected_at"])
    op.create_table(
        "source_health",
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("last_success", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure", sa.DateTime(timezone=True), nullable=True),
        sa.Column("average_response_time_ms", sa.Float(), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("temporary_disabled_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=80), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("source"),
    )


def downgrade() -> None:
    op.drop_table("source_health")
    op.drop_index("ix_search_snapshots_collected_at", table_name="search_snapshots")
    op.drop_index("ix_search_snapshots_dataset_hash", table_name="search_snapshots")
    op.drop_index("ix_search_snapshots_normalized_query", table_name="search_snapshots")
    op.drop_table("search_snapshots")
