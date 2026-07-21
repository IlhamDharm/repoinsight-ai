"""Add domain models for User, Repository, and Analysis

Revision ID: 4f1e2d3c5b6a
Revises: 19d1e7312e1d
Create Date: 2026-07-18 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "4f1e2d3c5b6a"
down_revision = "19d1e7312e1d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("github_username", sa.String(length=100), nullable=False, unique=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(op.f("ix_users_github_username"), "users", ["github_username"], unique=False)

    op.create_table(
        "repositories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("github_repo_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("url", sa.String(length=255), nullable=False),
        sa.Column("default_branch", sa.String(length=100), nullable=False),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(op.f("ix_repositories_owner_id"), "repositories", ["owner_id"], unique=False)
    op.create_index(op.f("ix_repositories_github_repo_id"), "repositories", ["github_repo_id"], unique=False)
    op.create_index(op.f("ix_repositories_full_name"), "repositories", ["full_name"], unique=False)

    op.create_table(
        "analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "RUNNING", "COMPLETED", "FAILED", name="analysis_status", native_enum=False),
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
    )
    op.create_index(op.f("ix_analyses_repository_id"), "analyses", ["repository_id"], unique=False)
    op.create_index(op.f("ix_analyses_status"), "analyses", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_analyses_status"), table_name="analyses")
    op.drop_index(op.f("ix_analyses_repository_id"), table_name="analyses")
    op.drop_table("analyses")
    op.drop_index(op.f("ix_repositories_full_name"), table_name="repositories")
    op.drop_index(op.f("ix_repositories_github_repo_id"), table_name="repositories")
    op.drop_index(op.f("ix_repositories_owner_id"), table_name="repositories")
    op.drop_table("repositories")
    op.drop_index(op.f("ix_users_github_username"), table_name="users")
    op.drop_table("users")
