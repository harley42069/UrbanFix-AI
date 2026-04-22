"""0003 add signalement pipeline tracking fields

Revision ID: 0003_signalement_pipeline_tracking
Revises: 0002_indexes_and_constraints
Create Date: 2026-03-14 14:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_signalement_pipeline_tracking"
down_revision = "0002_indexes_and_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("signalements") as batch_op:
        batch_op.add_column(sa.Column("progress", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("current_stage", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("last_error", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE signalements SET progress = 100 WHERE status = 'completed'")


def downgrade() -> None:
    with op.batch_alter_table("signalements") as batch_op:
        batch_op.drop_column("completed_at")
        batch_op.drop_column("last_error")
        batch_op.drop_column("current_stage")
        batch_op.drop_column("progress")
