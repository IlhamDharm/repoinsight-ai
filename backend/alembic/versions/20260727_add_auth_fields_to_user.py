"""Add authentication fields to User model

Revision ID: a1b2c3d4e5f6
Revises: 6b7c8d9e0f1a
Create Date: 2026-07-27 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "6b7c8d9e0f1a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old unique index on github_username first (will be recreated as nullable)
    op.drop_index(op.f("ix_users_github_username"), table_name="users")

    # Add new columns
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=False, server_default=""))
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))

    # Make email NOT NULL with unique constraint
    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=False)
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # Make github_username nullable
    op.alter_column("users", "github_username", existing_type=sa.String(length=100), nullable=True)

    # Recreate index on github_username (now nullable, still unique)
    op.create_index(op.f("ix_users_github_username"), "users", ["github_username"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_github_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_column("users", "is_active")
    op.drop_column("users", "password_hash")

    # Restore github_username to NOT NULL
    op.alter_column("users", "github_username", existing_type=sa.String(length=100), nullable=False)

    # Restore email to nullable
    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=True)

    # Recreate original index
    op.create_index(op.f("ix_users_github_username"), "users", ["github_username"], unique=False)
