"""Models-owned versioned configuration, calls, stream checkpoints and reservations."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from accos.adapters.persistence.models import Base, JSON_TYPE, SCHEMA_NAME


class ConfigurationColumns:
    workspace_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ModelProfileRow(ConfigurationColumns, Base):
    __tablename__ = "model_profiles"
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_model_profile_version"),
        {"schema": SCHEMA_NAME},
    )


class ModelPolicyRow(ConfigurationColumns, Base):
    __tablename__ = "model_policies"
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_model_policy_version"),
        {"schema": SCHEMA_NAME},
    )


class ModelBudgetSettingsRow(Base):
    __tablename__ = "model_budget_settings"
    workspace_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    updated_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_model_budget_version"),
        {"schema": SCHEMA_NAME},
    )


class PromptVersionRow(Base):
    __tablename__ = "prompt_versions"
    workspace_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    version: Mapped[str] = mapped_column(String(30), primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = ({"schema": SCHEMA_NAME},)


class ModelCallRow(Base):
    __tablename__ = "model_calls"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    actor_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    operation_key: Mapped[str] = mapped_column(String(128), nullable=False)
    digest: Mapped[str] = mapped_column(String(64), nullable=False)
    cache_key: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    record: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    security_headers: Mapped[dict[str, str]] = mapped_column(JSON_TYPE, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "actor_id",
            "operation_key",
            name="uq_model_call_operation",
        ),
        ForeignKeyConstraint(
            ["project_id"], [f"{SCHEMA_NAME}.projects.id"], name="fk_model_call_project"
        ),
        CheckConstraint("sequence >= 0", name="ck_model_call_sequence"),
        Index("ix_model_call_history", "workspace_id", "project_id", "created_at", "id"),
        Index("ix_model_call_queue", "status", "lease_until", "created_at"),
        Index("ix_model_call_cache", "workspace_id", "project_id", "cache_key", "created_at"),
        {"schema": SCHEMA_NAME},
    )


class ModelCallEventRow(Base):
    __tablename__ = "model_call_events"
    call_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["call_id"], [f"{SCHEMA_NAME}.model_calls.id"], name="fk_model_event_call"
        ),
        Index("ix_model_event_scope", "workspace_id", "project_id", "call_id", "sequence"),
        {"schema": SCHEMA_NAME},
    )


class BudgetReservationRow(Base):
    __tablename__ = "budget_reservations"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    task_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    call_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    day: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    token_debit: Mapped[int] = mapped_column(BigInteger, nullable=False)
    money_debit: Mapped[int] = mapped_column(BigInteger, nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    reconciliation: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    __table_args__ = (
        UniqueConstraint("call_id", "attempt", name="uq_model_attempt_reservation"),
        ForeignKeyConstraint(["call_id"], [f"{SCHEMA_NAME}.model_calls.id"], name="fk_budget_call"),
        CheckConstraint(
            "token_debit >= 0 AND money_debit >= 0 AND attempt > 0", name="ck_budget_debits"
        ),
        CheckConstraint(
            "status IN ('reserved','settled','released','unknown')", name="ck_budget_state"
        ),
        Index("ix_budget_workspace_day", "workspace_id", "day"),
        Index("ix_budget_workspace_task", "workspace_id", "task_id"),
        {"schema": SCHEMA_NAME},
    )
