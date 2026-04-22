"""0004 add signalement JSON result columns and FAILED status

Adds denormalized JSON result columns (detections, scenarios,
estimations), media URL columns (audio_url, video_url, pdf_url),
processing_time_seconds, and the 'failed' value to the status enum.

Revision ID: 0004_signalement_json_results
Revises: 0003_signalement_pipeline_tracking
Create Date: 2026-03-15 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_signalement_json_results"
down_revision = "0003_signalement_pipeline_tracking"
branch_labels = None
depends_on = None

# New enum including 'failed' (used for SQLite batch recreation)
_NEW_STATUS_TYPE = sa.Enum(
    "pending",
    "processing",
    "completed",
    "failed",
    "rejected",
    name="signalement_status_enum",
    create_constraint=True,
)

_OLD_STATUS_TYPE = sa.Enum(
    "pending",
    "processing",
    "completed",
    "rejected",
    name="signalement_status_enum",
    create_constraint=True,
)


def _add_result_columns(batch_op: object) -> None:  # type: ignore[type-arg]
    """Helper: add the 7 new columns inside a batch context."""
    batch_op.add_column(sa.Column("detections", sa.JSON(), nullable=True))
    batch_op.add_column(sa.Column("scenarios", sa.JSON(), nullable=True))
    batch_op.add_column(sa.Column("estimations", sa.JSON(), nullable=True))
    batch_op.add_column(sa.Column("audio_url", sa.String(length=1024), nullable=True))
    batch_op.add_column(sa.Column("video_url", sa.String(length=1024), nullable=True))
    batch_op.add_column(sa.Column("pdf_url", sa.String(length=1024), nullable=True))
    batch_op.add_column(sa.Column("processing_time_seconds", sa.Float(), nullable=True))


def _drop_result_columns(batch_op: object) -> None:  # type: ignore[type-arg]
    """Helper: drop the 7 columns inside a batch context."""
    batch_op.drop_column("processing_time_seconds")
    batch_op.drop_column("pdf_url")
    batch_op.drop_column("video_url")
    batch_op.drop_column("audio_url")
    batch_op.drop_column("estimations")
    batch_op.drop_column("scenarios")
    batch_op.drop_column("detections")


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        # Add the 'failed' value to the native PostgreSQL enum type.
        # IF NOT EXISTS prevents errors on repeated runs.
        bind.execute(
            sa.text(
                "ALTER TYPE signalement_status_enum ADD VALUE IF NOT EXISTS 'failed' "
                "BEFORE 'rejected'"
            )
        )
        # For PostgreSQL we only need to add columns — no table rebuild required.
        with op.batch_alter_table("signalements") as batch_op:
            _add_result_columns(batch_op)
    else:
        # SQLite: rebuild the table so the CHECK constraint is updated to include 'failed'.
        with op.batch_alter_table("signalements", recreate="always") as batch_op:
            batch_op.alter_column(
                "status",
                existing_type=_OLD_STATUS_TYPE,
                type_=_NEW_STATUS_TYPE,
                existing_nullable=False,
            )
            _add_result_columns(batch_op)


def downgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        # PostgreSQL does not support removing enum values natively.
        # Drop and recreate the type would require disabling dependent columns —
        # log a warning instead and only drop the new columns.
        import warnings
        warnings.warn(
            "Downgrade 0004: PostgreSQL enum value 'failed' cannot be removed automatically. "
            "If needed, remove it manually: ALTER TYPE signalement_status_enum RENAME TO …, "
            "then recreate without 'failed'.",
            stacklevel=2,
        )
        with op.batch_alter_table("signalements") as batch_op:
            _drop_result_columns(batch_op)
    else:
        # SQLite: rebuild without the new columns and restore old CHECK constraint.
        with op.batch_alter_table("signalements", recreate="always") as batch_op:
            batch_op.alter_column(
                "status",
                existing_type=_NEW_STATUS_TYPE,
                type_=_OLD_STATUS_TYPE,
                existing_nullable=False,
            )
            _drop_result_columns(batch_op)
