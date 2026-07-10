"""initial schema"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("email", sa.String(320), unique=True, nullable=False, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "tickets",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("public_reference", sa.String(32), unique=True, nullable=False, index=True),
        sa.Column("customer_name", sa.String(160), nullable=False),
        sa.Column("customer_email", sa.String(320), nullable=False, index=True),
        sa.Column("customer_phone", sa.String(64)),
        sa.Column("device_type", sa.String(80), nullable=False),
        sa.Column("device_model", sa.String(120)),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("description_fingerprint", sa.String(64), nullable=False, index=True),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("priority", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, index=True),
        sa.Column("ai_summary", sa.Text()),
        sa.Column("suggested_action", sa.Text()),
        sa.Column("ai_confidence", sa.Float()),
        sa.Column("requires_manual_review", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sla_due_at", sa.DateTime(timezone=True)),
        sa.Column("assigned_to", sa.String(160)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "ticket_events",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("ticket_id", sa.UUID(), sa.ForeignKey("tickets.id", ondelete="CASCADE"), index=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("event_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "attachments",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("ticket_id", sa.UUID(), sa.ForeignKey("tickets.id", ondelete="CASCADE"), index=True),
        sa.Column("object_key", sa.String(512), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "automation_runs",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("workflow_name", sa.String(120), nullable=False, index=True),
        sa.Column("correlation_id", sa.String(120), nullable=False, index=True),
        sa.Column("ticket_id", sa.UUID(), sa.ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    for table in ["automation_runs", "attachments", "ticket_events", "tickets", "users"]:
        op.drop_table(table)
