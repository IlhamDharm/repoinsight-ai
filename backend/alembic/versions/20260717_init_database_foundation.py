"""Initialize database foundation

Revision ID: 19d1e7312e1d
Revises: 
Create Date: 2026-07-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "19d1e7312e1d"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "infra_health_checks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="ok", nullable=False),
        sa.Column("checked_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_infra_health_checks_name"),
    )
    op.create_index(op.f("ix_infra_health_checks_name"), "infra_health_checks", ["name"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_infra_health_checks_name"), table_name="infra_health_checks")
    op.drop_table("infra_health_checks")
