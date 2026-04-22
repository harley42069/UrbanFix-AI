"""0002 indexes and constraints

Revision ID: 0002_indexes_and_constraints
Revises: 0001_initial_tables
Create Date: 2026-03-14 00:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_indexes_and_constraints"
down_revision = "0001_initial_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_users_created_at", "users", ["created_at"], unique=False)
    op.create_index("ix_users_is_deleted", "users", ["is_deleted"], unique=False)

    op.create_index("ix_signalements_user_id", "signalements", ["user_id"], unique=False)
    op.create_index("ix_signalements_status", "signalements", ["status"], unique=False)
    op.create_index("ix_signalements_created_at", "signalements", ["created_at"], unique=False)
    op.create_index("ix_signalements_city", "signalements", ["city"], unique=False)
    op.create_index("ix_signalements_region", "signalements", ["region"], unique=False)
    op.create_index("ix_signalements_city_region", "signalements", ["city", "region"], unique=False)
    op.create_index("ix_signalements_is_deleted", "signalements", ["is_deleted"], unique=False)

    op.create_index("ix_detections_signalement_id", "detections", ["signalement_id"], unique=False)
    op.create_index("ix_detections_class_name", "detections", ["class_name"], unique=False)
    op.create_index("ix_detections_created_at", "detections", ["created_at"], unique=False)
    op.create_index("ix_detections_is_deleted", "detections", ["is_deleted"], unique=False)

    op.create_index("ix_estimations_signalement_id", "estimations", ["signalement_id"], unique=False)
    op.create_index("ix_estimations_scenario_type", "estimations", ["scenario_type"], unique=False)
    op.create_index("ix_estimations_created_at", "estimations", ["created_at"], unique=False)
    op.create_index("ix_estimations_is_deleted", "estimations", ["is_deleted"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_estimations_is_deleted", table_name="estimations")
    op.drop_index("ix_estimations_created_at", table_name="estimations")
    op.drop_index("ix_estimations_scenario_type", table_name="estimations")
    op.drop_index("ix_estimations_signalement_id", table_name="estimations")

    op.drop_index("ix_detections_is_deleted", table_name="detections")
    op.drop_index("ix_detections_created_at", table_name="detections")
    op.drop_index("ix_detections_class_name", table_name="detections")
    op.drop_index("ix_detections_signalement_id", table_name="detections")

    op.drop_index("ix_signalements_is_deleted", table_name="signalements")
    op.drop_index("ix_signalements_city_region", table_name="signalements")
    op.drop_index("ix_signalements_region", table_name="signalements")
    op.drop_index("ix_signalements_city", table_name="signalements")
    op.drop_index("ix_signalements_created_at", table_name="signalements")
    op.drop_index("ix_signalements_status", table_name="signalements")
    op.drop_index("ix_signalements_user_id", table_name="signalements")

    op.drop_index("ix_users_is_deleted", table_name="users")
    op.drop_index("ix_users_created_at", table_name="users")
