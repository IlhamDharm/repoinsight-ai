from __future__ import annotations

from datetime import datetime
from enum import Enum

import sqlalchemy as sa
from sqlalchemy import ForeignKey, String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AnalysisStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    github_username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)

    repositories: Mapped[list[Repository]] = relationship(back_populates="owner", lazy="selectin")


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    owner: Mapped[User] = relationship(back_populates="repositories", lazy="selectin")
    github_repo_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(100), nullable=False)
    visibility: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)

    analyses: Mapped[list[Analysis]] = relationship(back_populates="repository", lazy="selectin")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    repository: Mapped[Repository] = relationship(back_populates="analyses", lazy="selectin")
    status: Mapped[AnalysisStatus] = mapped_column(
        sa.Enum(AnalysisStatus, name="analysis_status", native_enum=False),
        nullable=False,
        server_default=sa.text("'PENDING'"),
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    summary: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    scores: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    findings: Mapped[list | None] = mapped_column(sa.JSON, nullable=True)
    recommendations: Mapped[list | None] = mapped_column(sa.JSON, nullable=True)
