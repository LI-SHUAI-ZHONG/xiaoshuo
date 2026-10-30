"""PostgreSQL and deterministic in-memory quality repositories."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - SQLAlchemy resolves annotations at runtime.
from typing import TYPE_CHECKING, cast
from uuid import UUID  # noqa: TC003 - SQLAlchemy resolves annotations at runtime.

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Uuid, select
from sqlalchemy.orm import Mapped, mapped_column

from accos.adapters.persistence.models import JSON_TYPE, SCHEMA_NAME, Base
from accos.adapters.persistence.outbox import SqlAlchemyOutboxWriter
from accos.kernel.errors import InvalidStateError
from accos.modules.quality.domain import (
    DimensionStatus,
    EvaluationRun,
    QualityResult,
    QualityStatus,
    RubricVersion,
    ScoreDimension,
)

if TYPE_CHECKING:
    from accos.adapters.persistence.database import AsyncSessionFactory
    from accos.kernel.events import EventEnvelope


class RubricVersionRow(Base):
    __tablename__ = "quality_rubric_versions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", name="fk_quality_rubrics_project"), nullable=False
    )
    rubric_key: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(40), nullable=False)
    dimension_keys: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index(
            "uq_quality_rubric_version",
            "workspace_id",
            "project_id",
            "rubric_key",
            "version",
            unique=True,
        ),
        {"schema": SCHEMA_NAME},
    )


class EvaluationRunRow(Base):
    __tablename__ = "quality_evaluation_runs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    rubric_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("quality_rubric_versions.id", name="fk_quality_runs_rubric"),
        nullable=False,
    )
    input_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    workflow_run_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    requested_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_quality_runs_scope", "workspace_id", "project_id", "created_at"),
        {"schema": SCHEMA_NAME},
    )


class QualityResultRow(Base):
    __tablename__ = "quality_results"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    evaluation_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("quality_evaluation_runs.id", name="fk_quality_results_run"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    evaluator_key: Mapped[str] = mapped_column(String(100), nullable=False)
    evaluator_version: Mapped[str] = mapped_column(String(40), nullable=False)
    dimensions: Mapped[list[dict[str, object]]] = mapped_column(JSON_TYPE, nullable=False)
    result_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_quality_results_scope", "workspace_id", "project_id", "status"),
        {"schema": SCHEMA_NAME},
    )


class InMemoryQualityRepository:
    def __init__(self) -> None:
        self.rubrics: dict[UUID, RubricVersion] = {}
        self.runs: dict[UUID, EvaluationRun] = {}
        self.results: dict[UUID, QualityResult] = {}
        self.events: list[EventEnvelope] = []

    async def add_rubric(self, rubric: RubricVersion) -> RubricVersion:
        existing = self.rubrics.get(rubric.id)
        if existing is not None:
            return existing
        self.rubrics[rubric.id] = rubric
        return rubric

    async def get_rubric(
        self, workspace_id: UUID, project_id: UUID, rubric_id: UUID
    ) -> RubricVersion | None:
        rubric = self.rubrics.get(rubric_id)
        if rubric is None or (rubric.workspace_id, rubric.project_id) != (
            workspace_id,
            project_id,
        ):
            return None
        return rubric

    async def add_run(self, run: EvaluationRun, event: EventEnvelope) -> EvaluationRun:
        existing = self.runs.get(run.id)
        if existing is not None:
            return existing
        self.runs[run.id] = run
        self.events.append(event)
        return run

    async def get_run(
        self, workspace_id: UUID, project_id: UUID, run_id: UUID
    ) -> EvaluationRun | None:
        run = self.runs.get(run_id)
        if run is None or (run.workspace_id, run.project_id) != (workspace_id, project_id):
            return None
        return run

    async def finish_run(
        self,
        run: EvaluationRun,
        result: QualityResult,
        event: EventEnvelope,
    ) -> tuple[EvaluationRun, QualityResult]:
        existing = self.runs.get(run.id)
        if existing is None or existing.status is not QualityStatus.NOT_RUN:
            raise InvalidStateError("Quality evaluation is unavailable or already completed.")
        self.runs[run.id] = run
        self.results[run.id] = result
        self.events.append(event)
        return run, result

    async def get_result(
        self, workspace_id: UUID, project_id: UUID, run_id: UUID
    ) -> QualityResult | None:
        result = self.results.get(run_id)
        if result is None or (result.workspace_id, result.project_id) != (
            workspace_id,
            project_id,
        ):
            return None
        return result


class SqlAlchemyQualityRepository:
    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def add_rubric(self, rubric: RubricVersion) -> RubricVersion:
        async with self._sessions.begin() as session:
            existing = await session.get(RubricVersionRow, rubric.id)
            if existing is not None:
                return _rubric(existing)
            session.add(_rubric_row(rubric))
        return rubric

    async def get_rubric(
        self, workspace_id: UUID, project_id: UUID, rubric_id: UUID
    ) -> RubricVersion | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(RubricVersionRow).where(
                    RubricVersionRow.workspace_id == workspace_id,
                    RubricVersionRow.project_id == project_id,
                    RubricVersionRow.id == rubric_id,
                )
            )
        return None if row is None else _rubric(row)

    async def add_run(self, run: EvaluationRun, event: EventEnvelope) -> EvaluationRun:
        async with self._sessions.begin() as session:
            existing = await session.get(EvaluationRunRow, run.id)
            if existing is not None:
                return _run(existing)
            session.add(_run_row(run))
            await SqlAlchemyOutboxWriter(session).append(event)
        return run

    async def get_run(
        self, workspace_id: UUID, project_id: UUID, run_id: UUID
    ) -> EvaluationRun | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(EvaluationRunRow).where(
                    EvaluationRunRow.workspace_id == workspace_id,
                    EvaluationRunRow.project_id == project_id,
                    EvaluationRunRow.id == run_id,
                )
            )
        return None if row is None else _run(row)

    async def finish_run(
        self,
        run: EvaluationRun,
        result: QualityResult,
        event: EventEnvelope,
    ) -> tuple[EvaluationRun, QualityResult]:
        async with self._sessions.begin() as session:
            row = await session.scalar(
                select(EvaluationRunRow)
                .where(
                    EvaluationRunRow.workspace_id == run.workspace_id,
                    EvaluationRunRow.project_id == run.project_id,
                    EvaluationRunRow.id == run.id,
                )
                .with_for_update()
            )
            if row is None or row.status != QualityStatus.NOT_RUN.value:
                raise InvalidStateError("Quality evaluation is unavailable or already completed.")
            row.status = run.status.value
            row.completed_at = run.completed_at
            session.add(_result_row(result))
            await SqlAlchemyOutboxWriter(session).append(event)
        return run, result

    async def get_result(
        self, workspace_id: UUID, project_id: UUID, run_id: UUID
    ) -> QualityResult | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(QualityResultRow).where(
                    QualityResultRow.workspace_id == workspace_id,
                    QualityResultRow.project_id == project_id,
                    QualityResultRow.evaluation_run_id == run_id,
                )
            )
        return None if row is None else _result(row)


def _rubric_row(item: RubricVersion) -> RubricVersionRow:
    return RubricVersionRow(
        id=item.id,
        workspace_id=item.workspace_id,
        project_id=item.project_id,
        rubric_key=item.rubric_key,
        version=item.version,
        schema_version=item.schema_version,
        dimension_keys=list(item.dimension_keys),
        created_by=item.created_by,
        created_at=item.created_at,
    )


def _rubric(row: RubricVersionRow) -> RubricVersion:
    return RubricVersion(
        row.id,
        row.workspace_id,
        row.project_id,
        row.rubric_key,
        row.version,
        row.schema_version,
        tuple(row.dimension_keys),
        row.created_by,
        row.created_at,
    )


def _run_row(item: EvaluationRun) -> EvaluationRunRow:
    return EvaluationRunRow(
        id=item.id,
        workspace_id=item.workspace_id,
        project_id=item.project_id,
        rubric_id=item.rubric_id,
        input_reference=item.input_reference,
        workflow_run_id=item.workflow_run_id,
        requested_by=item.requested_by,
        status=item.status.value,
        created_at=item.created_at,
        completed_at=item.completed_at,
    )


def _run(row: EvaluationRunRow) -> EvaluationRun:
    return EvaluationRun(
        row.id,
        row.workspace_id,
        row.project_id,
        row.rubric_id,
        row.input_reference,
        row.workflow_run_id,
        row.requested_by,
        QualityStatus(row.status),
        row.created_at,
        row.completed_at,
    )


def _result_row(item: QualityResult) -> QualityResultRow:
    return QualityResultRow(
        id=item.id,
        workspace_id=item.workspace_id,
        project_id=item.project_id,
        evaluation_run_id=item.evaluation_run_id,
        status=item.status.value,
        evaluator_key=item.evaluator_key,
        evaluator_version=item.evaluator_version,
        dimensions=[
            {"key": value.key, "status": value.status.value, "score": value.score}
            for value in item.dimensions
        ],
        result_reference=item.result_reference,
        created_at=item.created_at,
    )


def _result(row: QualityResultRow) -> QualityResult:
    return QualityResult(
        row.id,
        row.workspace_id,
        row.project_id,
        row.evaluation_run_id,
        QualityStatus(row.status),
        row.evaluator_key,
        row.evaluator_version,
        tuple(
            ScoreDimension(
                str(item["key"]),
                DimensionStatus(str(item["status"])),
                None if item["score"] is None else float(cast("float", item["score"])),
            )
            for item in row.dimensions
        ),
        row.result_reference,
        row.created_at,
    )


MODEL_REGISTRY = (RubricVersionRow, EvaluationRunRow, QualityResultRow)
