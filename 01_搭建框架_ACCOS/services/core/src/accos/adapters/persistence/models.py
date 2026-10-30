"""Private SQLAlchemy models for execution 05 technical tables."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
    Identity,
    Index,
    Integer,
    MetaData,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SCHEMA_NAME = "accos"
PENDING_STATUS = "pending"
LEASED_STATUS = "leased"
PUBLISHED_STATUS = "published"
JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


def utc_now() -> datetime:
    """Return an aware UTC value for ORM-side defaults."""
    return datetime.now(tz=UTC)


class Base(DeclarativeBase):
    """Metadata root kept private to the persistence adapter."""

    metadata = MetaData(schema=SCHEMA_NAME)


class ScopedRecordMixin:
    """Common identity, scope, time, and soft-archive columns for scoped records."""

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OutboxEventRow(ScopedRecordMixin, Base):
    """Durable event awaiting at-least-once publication."""

    __tablename__ = "outbox_events"

    sequence: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), nullable=False, unique=True
    )
    aggregate_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    event_type: Mapped[str] = mapped_column(String(200), nullable=False)
    event_version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=PENDING_STATUS)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lease_token: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__: dict[str, object] = {"version_id_col": version}  # noqa: RUF012
    __table_args__ = (
        CheckConstraint("event_version > 0", name="ck_outbox_event_version_positive"),
        CheckConstraint("attempt_count >= 0", name="ck_outbox_attempt_count_non_negative"),
        CheckConstraint("version > 0", name="ck_outbox_version_positive"),
        CheckConstraint(
            "status IN ('pending', 'leased', 'published')",
            name="ck_outbox_status_valid",
        ),
        Index(
            "ix_outbox_events_relay",
            "status",
            "available_at",
            "lease_expires_at",
            "sequence",
        ),
        {"schema": SCHEMA_NAME},
    )


class IdempotencyRecordRow(ScopedRecordMixin, Base):
    """Scoped request fingerprint and its durable result reference."""

    __tablename__ = "idempotency_records"

    scope: Mapped[str] = mapped_column(String(100), nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    result_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__: dict[str, object] = {"version_id_col": version}  # noqa: RUF012
    __table_args__ = (
        UniqueConstraint("workspace_id", "scope", "key", name="uq_idempotency_workspace_scope_key"),
        CheckConstraint("version > 0", name="ck_idempotency_version_positive"),
        Index("ix_idempotency_records_expiry", "expires_at"),
        {"schema": SCHEMA_NAME},
    )


class SchemaMetadataRow(Base):
    """Application-owned migration audit metadata."""

    __tablename__ = "schema_metadata"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    component: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    revision: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__: dict[str, object] = {"version_id_col": version}  # noqa: RUF012
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_schema_metadata_version_positive"),
        {"schema": SCHEMA_NAME},
    )
