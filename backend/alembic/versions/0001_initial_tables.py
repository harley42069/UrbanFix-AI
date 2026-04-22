"""0001 initial tables

Revision ID: 0001_initial_tables
Revises: 
Create Date: 2026-03-14 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_tables"
down_revision = None
branch_labels = None
depends_on = None


user_role_enum = sa.Enum("citizen", "municipality", "admin", name="user_role_enum")
signalement_status_enum = sa.Enum(
    "pending", "processing", "completed", "rejected", name="signalement_status_enum"
)
scenario_type_enum = sa.Enum("minimal", "moderate", "premium", name="scenario_type_enum")


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        user_role_enum.create(bind, checkfirst=True)
        signalement_status_enum.create(bind, checkfirst=True)
        scenario_type_enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )

    op.create_table(
        "signalements",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_path", sa.String(length=512), nullable=False),
        sa.Column("image_url", sa.String(length=1024), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=False),
        sa.Column("status", signalement_status_enum, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
    )

    op.create_table(
        "detections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("signalement_id", sa.Integer(), nullable=False),
        sa.Column("class_name", sa.String(length=100), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("bbox_x", sa.Float(), nullable=False),
        sa.Column("bbox_y", sa.Float(), nullable=False),
        sa.Column("bbox_width", sa.Float(), nullable=False),
        sa.Column("bbox_height", sa.Float(), nullable=False),
        sa.Column("image_annotated_path", sa.String(length=512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.ForeignKeyConstraint(["signalement_id"], ["signalements.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "estimations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("signalement_id", sa.Integer(), nullable=False),
        sa.Column("scenario_type", scenario_type_enum, nullable=False),
        sa.Column("total_cost_min", sa.Float(), nullable=False),
        sa.Column("total_cost_max", sa.Float(), nullable=False),
        sa.Column("total_cost_avg", sa.Float(), nullable=False),
        sa.Column("breakdown", sa.JSON(), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=True),
        sa.Column("priority_score", sa.Float(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_scenario_path", sa.String(length=512), nullable=True),
        sa.Column("image_scenario_url", sa.String(length=1024), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.ForeignKeyConstraint(["signalement_id"], ["signalements.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.drop_table("estimations")
    op.drop_table("detections")
    op.drop_table("signalements")
    op.drop_table("users")

    if dialect == "postgresql":
        scenario_type_enum.drop(bind, checkfirst=True)
        signalement_status_enum.drop(bind, checkfirst=True)
        user_role_enum.drop(bind, checkfirst=True)
