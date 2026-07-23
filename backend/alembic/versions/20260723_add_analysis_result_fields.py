"""Add result fields (summary, scores, findings, recommendations) to Analysis model

Revision ID: 5a6b7c8d9e0f
Revises: 4f1e2d3c5b6a
Create Date: 2026-07-23 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "5a6b7c8d9e0f"
down_revision = "4f1e2d3c5b6a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analyses", sa.Column("summary", sa.JSON(), nullable=True))
    op.add_column("analyses", sa.Column("scores", sa.JSON(), nullable=True))
    op.add_column("analyses", sa.Column("findings", sa.JSON(), nullable=True))
    op.add_column("analyses", sa.Column("recommendations", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("analyses", "recommendations")
    op.drop_column("analyses", "findings")
    op.drop_column("analyses", "scores")
    op.drop_column("analyses", "summary")
