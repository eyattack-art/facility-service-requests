"""init tables

Revision ID: 1c3012c9ca42
Revises:
Create Date: 2026-08-13 19:04:17.577410

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "1c3012c9ca42"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "facilities",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_facilities")),
        sa.UniqueConstraint("name", name=op.f("uq_facilities_name")),
    )
    op.create_table(
        "users",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("facility_id", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(role = 'employee' AND facility_id IS NOT NULL) OR (role != 'employee' AND facility_id IS NULL)",
            name=op.f("ck_users_facility_id_by_role"),
        ),
        sa.CheckConstraint(
            "role IN ('employee', 'technician', 'manager')", name=op.f("ck_users_role")
        ),
        sa.ForeignKeyConstraint(
            ["facility_id"],
            ["facilities.id"],
            name=op.f("fk_users_facility_id_facilities"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_table(
        "service_requests",
        sa.Column("facility_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("assignee_id", sa.Uuid(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "category IN ('equipment', 'electricity', 'plumbing', 'premises', 'other')",
            name=op.f("ck_service_requests_category"),
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'critical')",
            name=op.f("ck_service_requests_priority"),
        ),
        sa.CheckConstraint(
            "status IN ('new', 'assigned', 'in_progress', 'completed', 'cancelled')",
            name=op.f("ck_service_requests_status"),
        ),
        sa.CheckConstraint(
            "cancellation_reason IS NULL OR char_length(trim(cancellation_reason)) <= 1000",
            name=op.f("ck_service_requests_cancellation_reason_length"),
        ),
        sa.CheckConstraint(
            "char_length(trim(description)) BETWEEN 10 AND 4000",
            name=op.f("ck_service_requests_description_length"),
        ),
        sa.CheckConstraint(
            "char_length(trim(title)) BETWEEN 5 AND 200",
            name=op.f("ck_service_requests_title_length"),
        ),
        sa.CheckConstraint(
            "result IS NULL OR char_length(trim(result)) <= 4000",
            name=op.f("ck_service_requests_result_length"),
        ),
        sa.ForeignKeyConstraint(
            ["assignee_id"],
            ["users.id"],
            name=op.f("fk_service_requests_assignee_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name=op.f("fk_service_requests_author_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["facility_id"],
            ["facilities.id"],
            name=op.f("fk_service_requests_facility_id_facilities"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_service_requests")),
    )
    op.create_index(
        "ix_service_requests_assignee_created",
        "service_requests",
        ["assignee_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_service_requests_facility_created",
        "service_requests",
        ["facility_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_service_requests_status_created",
        "service_requests",
        ["status", "created_at"],
        unique=False,
    )
    op.create_table(
        "status_history",
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("old_status", sa.String(length=20), nullable=True),
        sa.Column("new_status", sa.String(length=20), nullable=False),
        sa.Column("changed_by", sa.Uuid(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "new_status IN ('new', 'assigned', 'in_progress', 'completed', 'cancelled')",
            name=op.f("ck_status_history_new_status"),
        ),
        sa.CheckConstraint(
            "old_status IS NULL OR old_status IN ('new', 'assigned', 'in_progress', 'completed', 'cancelled')",
            name=op.f("ck_status_history_old_status"),
        ),
        sa.CheckConstraint(
            "comment IS NULL OR char_length(comment) <= 1000",
            name=op.f("ck_status_history_comment_length"),
        ),
        sa.ForeignKeyConstraint(
            ["changed_by"],
            ["users.id"],
            name=op.f("fk_status_history_changed_by_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["service_requests.id"],
            name=op.f("fk_status_history_request_id_service_requests"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_status_history")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("status_history")
    op.drop_index("ix_service_requests_status_created", table_name="service_requests")
    op.drop_index("ix_service_requests_facility_created", table_name="service_requests")
    op.drop_index("ix_service_requests_assignee_created", table_name="service_requests")
    op.drop_table("service_requests")
    op.drop_table("users")
    op.drop_table("facilities")
