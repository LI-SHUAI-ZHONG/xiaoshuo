"""Consent-aware in-memory and PostgreSQL feedback persistence."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime  # noqa: TC003 - SQLAlchemy resolves annotations at runtime.
from typing import TYPE_CHECKING, cast
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column

from accos.adapters.persistence.models import JSON_TYPE, SCHEMA_NAME, Base
from accos.adapters.persistence.outbox import SqlAlchemyOutboxWriter
from accos.kernel.errors import InvalidStateError
from accos.modules.feedback.domain import (
    ArtifactKind,
    BehaviorConsent,
    ConsentStatus,
    DerivedArtifactTombstone,
    DiagnosticFinding,
    DiagnosticSeverity,
    Experiment,
    ExperimentSample,
    ExperimentStatus,
    FeedbackEvent,
    FeedbackSource,
    FeedbackStatus,
    MetricDefinition,
    MetricDimension,
    MetricPoint,
    MetricSensitivity,
    TombstoneAction,
    Variant,
    WithdrawalResult,
)

if TYPE_CHECKING:
    from accos.adapters.persistence.database import AsyncSessionFactory
    from accos.kernel.events import EventEnvelope


class BehaviorConsentRow(Base):
    __tablename__ = "feedback_behavior_consents"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", name="fk_feedback_consents_project"), nullable=False
    )
    actor_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "ix_feedback_consents_scope",
            "workspace_id",
            "project_id",
            "actor_id",
            "granted_at",
        ),
        {"schema": SCHEMA_NAME},
    )


class FeedbackEventRow(Base):
    __tablename__ = "feedback_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", name="fk_feedback_events_project"), nullable=False
    )
    actor_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(100), nullable=False)
    signal_code: Mapped[str] = mapped_column(String(100), nullable=False)
    numeric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    consent_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("feedback_behavior_consents.id", name="fk_feedback_events_consent"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    creator_signal_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_feedback_events_scope", "workspace_id", "project_id", "source", "status"),
        {"schema": SCHEMA_NAME},
    )


class MetricDefinitionRow(Base):
    __tablename__ = "feedback_metric_definitions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", name="fk_feedback_metric_definitions_project"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    unit: Mapped[str] = mapped_column(String(100), nullable=False)
    dimensions: Mapped[list[dict[str, object]]] = mapped_column(JSON_TYPE, nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    sensitivity: Mapped[str] = mapped_column(String(20), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index(
            "uq_feedback_metric_definition",
            "workspace_id",
            "project_id",
            "name",
            "version",
            unique=True,
        ),
        {"schema": SCHEMA_NAME},
    )


class MetricPointRow(Base):
    __tablename__ = "feedback_metric_points"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    metric_definition_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("feedback_metric_definitions.id", name="fk_feedback_points_definition"),
        nullable=False,
    )
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    dimensions: Mapped[list[list[str]]] = mapped_column(JSON_TYPE, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    source_feedback_event_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("feedback_events.id", name="fk_feedback_points_event"),
        nullable=True,
    )
    included: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tombstoned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "ix_feedback_points_scope", "workspace_id", "project_id", "metric_name", "observed_at"
        ),
        {"schema": SCHEMA_NAME},
    )


class DiagnosticFindingRow(Base):
    __tablename__ = "feedback_diagnostic_findings"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    metric_point_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("feedback_metric_points.id", name="fk_feedback_diagnostics_point"),
        nullable=False,
    )
    rule_key: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(40), nullable=False)
    finding_code: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_value: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_feedback_diagnostics_scope", "workspace_id", "project_id", "severity"),
        {"schema": SCHEMA_NAME},
    )


class ExperimentRow(Base):
    __tablename__ = "feedback_experiments"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", name="fk_feedback_experiments_project"), nullable=False
    )
    experiment_key: Mapped[str] = mapped_column(String(100), nullable=False)
    protocol_version: Mapped[str] = mapped_column(String(40), nullable=False)
    hypothesis_code: Mapped[str] = mapped_column(String(100), nullable=False)
    primary_metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sample_scope: Mapped[str] = mapped_column(String(40), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stop_condition_codes: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    result_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index(
            "uq_feedback_experiment_version",
            "workspace_id",
            "project_id",
            "experiment_key",
            "protocol_version",
            unique=True,
        ),
        {"schema": SCHEMA_NAME},
    )


class VariantRow(Base):
    __tablename__ = "feedback_experiment_variants"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    experiment_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("feedback_experiments.id", name="fk_feedback_variants_experiment"),
        nullable=False,
    )
    variant_key: Mapped[str] = mapped_column(String(100), nullable=False)
    configuration_reference: Mapped[str] = mapped_column(String(500), nullable=False)

    __table_args__ = (
        Index("uq_feedback_variant_key", "experiment_id", "variant_key", unique=True),
        {"schema": SCHEMA_NAME},
    )


class ExperimentSampleRow(Base):
    __tablename__ = "feedback_experiment_samples"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    experiment_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("feedback_experiments.id", name="fk_feedback_samples_experiment"),
        nullable=False,
    )
    variant_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("feedback_experiment_variants.id", name="fk_feedback_samples_variant"),
        nullable=False,
    )
    metric_point_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("feedback_metric_points.id", name="fk_feedback_samples_point"),
        nullable=False,
    )
    source_feedback_event_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("feedback_events.id", name="fk_feedback_samples_event"), nullable=True
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    included: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tombstoned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_feedback_samples_scope", "workspace_id", "project_id", "experiment_id"),
        {"schema": SCHEMA_NAME},
    )


class TombstoneRow(Base):
    __tablename__ = "feedback_tombstones"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    source_feedback_event_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("feedback_events.id", name="fk_feedback_tombstones_event"), nullable=False
    )
    artifact_kind: Mapped[str] = mapped_column(String(30), nullable=False)
    artifact_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_feedback_tombstones_scope", "workspace_id", "project_id", "created_at"),
        {"schema": SCHEMA_NAME},
    )


class InMemoryFeedbackRepository:
    def __init__(self) -> None:
        self.consents: dict[UUID, BehaviorConsent] = {}
        self.feedback: dict[UUID, FeedbackEvent] = {}
        self.definitions: dict[UUID, MetricDefinition] = {}
        self.points: dict[UUID, MetricPoint] = {}
        self.diagnostics: dict[UUID, DiagnosticFinding] = {}
        self.experiments: dict[UUID, Experiment] = {}
        self.variants: dict[UUID, Variant] = {}
        self.samples: dict[UUID, ExperimentSample] = {}
        self.tombstones: dict[UUID, DerivedArtifactTombstone] = {}
        self.events: list[EventEnvelope] = []

    async def add_consent(self, consent: BehaviorConsent, event: EventEnvelope) -> BehaviorConsent:
        existing = self.consents.get(consent.id)
        if existing is not None:
            return existing
        self.consents[consent.id] = consent
        self.events.append(event)
        return consent

    async def active_consent(
        self, workspace_id: UUID, project_id: UUID, actor_id: UUID
    ) -> BehaviorConsent | None:
        matches = [
            item
            for item in self.consents.values()
            if (item.workspace_id, item.project_id, item.actor_id, item.status)
            == (workspace_id, project_id, actor_id, ConsentStatus.ACTIVE)
        ]
        return max(matches, key=lambda item: item.granted_at, default=None)

    async def withdraw_consent(
        self,
        workspace_id: UUID,
        project_id: UUID,
        actor_id: UUID,
        *,
        withdrawn_at: datetime,
        event: EventEnvelope,
    ) -> WithdrawalResult:
        consent = await self.active_consent(workspace_id, project_id, actor_id)
        if consent is None:
            raise InvalidStateError("Behavior feedback consent is not active.")
        withdrawn = replace(consent, status=ConsentStatus.WITHDRAWN, withdrawn_at=withdrawn_at)
        self.consents[consent.id] = withdrawn
        event_ids: list[UUID] = []
        tombstones: list[DerivedArtifactTombstone] = []
        for item in tuple(self.feedback.values()):
            if (
                item.workspace_id,
                item.project_id,
                item.actor_id,
                item.source,
                item.status,
            ) != (
                workspace_id,
                project_id,
                actor_id,
                FeedbackSource.BEHAVIOR_CONSENTED,
                FeedbackStatus.ACTIVE,
            ):
                continue
            event_ids.append(item.id)
            self.feedback[item.id] = replace(
                item,
                actor_id=None,
                signal_code="withdrawn",
                numeric_value=None,
                source_reference=None,
                consent_id=None,
                status=FeedbackStatus.ANONYMIZED,
                creator_signal_reference=None,
            )
            tombstones.extend(self._exclude_derivatives(item, withdrawn_at))
        self.events.append(event)
        return WithdrawalResult(withdrawn, tuple(event_ids), tuple(tombstones))

    def _exclude_derivatives(
        self, source: FeedbackEvent, now: datetime
    ) -> list[DerivedArtifactTombstone]:
        created: list[DerivedArtifactTombstone] = []
        for point in tuple(self.points.values()):
            if point.source_feedback_event_id == source.id and point.included:
                self.points[point.id] = replace(point, included=False, tombstoned_at=now)
                created.append(
                    self._tombstone(
                        source,
                        ArtifactKind.METRIC_POINT,
                        point.reference,
                        TombstoneAction.RECOMPUTE,
                        now,
                    )
                )
        for sample in tuple(self.samples.values()):
            if sample.source_feedback_event_id == source.id and sample.included:
                self.samples[sample.id] = replace(sample, included=False, tombstoned_at=now)
                created.append(
                    self._tombstone(
                        source,
                        ArtifactKind.EXPERIMENT_SAMPLE,
                        f"experiment-sample://{sample.id}",
                        TombstoneAction.EXCLUDE,
                        now,
                    )
                )
        if source.creator_signal_reference is not None:
            created.append(
                self._tombstone(
                    source,
                    ArtifactKind.CREATOR_SIGNAL,
                    source.creator_signal_reference,
                    TombstoneAction.EXCLUDE,
                    now,
                )
            )
        return created

    def _tombstone(
        self,
        source: FeedbackEvent,
        kind: ArtifactKind,
        reference: str,
        action: TombstoneAction,
        now: datetime,
    ) -> DerivedArtifactTombstone:
        item = DerivedArtifactTombstone(
            uuid5(NAMESPACE_URL, f"accos:{source.id}:{kind.value}:{reference}"),
            source.workspace_id,
            source.project_id,
            source.id,
            kind,
            reference,
            action,
            "behavior-consent-withdrawn",
            now,
        )
        self.tombstones[item.id] = item
        return item

    async def add_feedback(self, item: FeedbackEvent, event: EventEnvelope) -> FeedbackEvent:
        existing = self.feedback.get(item.id)
        if existing is not None:
            return existing
        self.feedback[item.id] = item
        self.events.append(event)
        return item

    async def get_feedback(
        self, workspace_id: UUID, project_id: UUID, event_id: UUID
    ) -> FeedbackEvent | None:
        item = self.feedback.get(event_id)
        if item is None or (item.workspace_id, item.project_id) != (workspace_id, project_id):
            return None
        return item

    async def add_metric_definition(self, item: MetricDefinition) -> MetricDefinition:
        existing = self.definitions.get(item.id)
        if existing is not None:
            return existing
        self.definitions[item.id] = item
        return item

    async def add_metric_point(self, item: MetricPoint, event: EventEnvelope) -> MetricPoint:
        existing = self.points.get(item.id)
        if existing is not None:
            return existing
        self.points[item.id] = item
        self.events.append(event)
        return item

    async def get_metric_point(
        self, workspace_id: UUID, project_id: UUID, point_id: UUID
    ) -> MetricPoint | None:
        item = self.points.get(point_id)
        if item is None or (item.workspace_id, item.project_id) != (workspace_id, project_id):
            return None
        return item

    async def add_diagnostic(
        self, item: DiagnosticFinding, event: EventEnvelope
    ) -> DiagnosticFinding:
        existing = self.diagnostics.get(item.id)
        if existing is not None:
            return existing
        self.diagnostics[item.id] = item
        self.events.append(event)
        return item

    async def get_diagnostic(
        self, workspace_id: UUID, project_id: UUID, finding_id: UUID
    ) -> DiagnosticFinding | None:
        item = self.diagnostics.get(finding_id)
        if item is None or (item.workspace_id, item.project_id) != (workspace_id, project_id):
            return None
        return item

    async def add_experiment(
        self, item: Experiment, variants: tuple[Variant, ...], event: EventEnvelope
    ) -> tuple[Experiment, tuple[Variant, ...]]:
        existing = self.experiments.get(item.id)
        if existing is not None:
            current = tuple(
                value for value in self.variants.values() if value.experiment_id == item.id
            )
            return existing, tuple(sorted(current, key=lambda value: value.variant_key))
        self.experiments[item.id] = item
        self.variants.update({variant.id: variant for variant in variants})
        self.events.append(event)
        return item, variants

    async def get_experiment(
        self, workspace_id: UUID, project_id: UUID, experiment_id: UUID
    ) -> tuple[Experiment, tuple[Variant, ...]] | None:
        item = self.experiments.get(experiment_id)
        if item is None or (item.workspace_id, item.project_id) != (workspace_id, project_id):
            return None
        variants = tuple(
            sorted(
                (value for value in self.variants.values() if value.experiment_id == item.id),
                key=lambda value: value.variant_key,
            )
        )
        return item, variants

    async def transition_experiment(
        self,
        item: Experiment,
        expected_status: ExperimentStatus,
        event: EventEnvelope,
    ) -> Experiment:
        existing = self.experiments.get(item.id)
        if existing is None or existing.status is not expected_status:
            raise InvalidStateError("Experiment is unavailable or changed concurrently.")
        self.experiments[item.id] = item
        self.events.append(event)
        return item

    async def add_sample(self, item: ExperimentSample, event: EventEnvelope) -> ExperimentSample:
        existing = self.samples.get(item.id)
        if existing is not None:
            return existing
        self.samples[item.id] = item
        self.events.append(event)
        return item


class SqlAlchemyFeedbackRepository:
    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def add_consent(self, consent: BehaviorConsent, event: EventEnvelope) -> BehaviorConsent:
        async with self._sessions.begin() as session:
            existing = await session.get(BehaviorConsentRow, consent.id)
            if existing is not None:
                return _consent(existing)
            session.add(_consent_row(consent))
            await SqlAlchemyOutboxWriter(session).append(event)
        return consent

    async def active_consent(
        self, workspace_id: UUID, project_id: UUID, actor_id: UUID
    ) -> BehaviorConsent | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(BehaviorConsentRow)
                .where(
                    BehaviorConsentRow.workspace_id == workspace_id,
                    BehaviorConsentRow.project_id == project_id,
                    BehaviorConsentRow.actor_id == actor_id,
                    BehaviorConsentRow.status == ConsentStatus.ACTIVE.value,
                )
                .order_by(BehaviorConsentRow.granted_at.desc())
                .limit(1)
            )
        return None if row is None else _consent(row)

    async def withdraw_consent(
        self,
        workspace_id: UUID,
        project_id: UUID,
        actor_id: UUID,
        *,
        withdrawn_at: datetime,
        event: EventEnvelope,
    ) -> WithdrawalResult:
        async with self._sessions.begin() as session:
            consent_row = await session.scalar(
                select(BehaviorConsentRow)
                .where(
                    BehaviorConsentRow.workspace_id == workspace_id,
                    BehaviorConsentRow.project_id == project_id,
                    BehaviorConsentRow.actor_id == actor_id,
                    BehaviorConsentRow.status == ConsentStatus.ACTIVE.value,
                )
                .order_by(BehaviorConsentRow.granted_at.desc())
                .limit(1)
                .with_for_update()
            )
            if consent_row is None:
                raise InvalidStateError("Behavior feedback consent is not active.")
            consent_row.status = ConsentStatus.WITHDRAWN.value
            consent_row.withdrawn_at = withdrawn_at
            feedback_rows = tuple(
                await session.scalars(
                    select(FeedbackEventRow)
                    .where(
                        FeedbackEventRow.workspace_id == workspace_id,
                        FeedbackEventRow.project_id == project_id,
                        FeedbackEventRow.actor_id == actor_id,
                        FeedbackEventRow.source == FeedbackSource.BEHAVIOR_CONSENTED.value,
                        FeedbackEventRow.status == FeedbackStatus.ACTIVE.value,
                    )
                    .with_for_update()
                )
            )
            tombstones: list[DerivedArtifactTombstone] = []
            for feedback_row in feedback_rows:
                creator_reference = feedback_row.creator_signal_reference
                feedback_row.actor_id = None
                feedback_row.signal_code = "withdrawn"
                feedback_row.numeric_value = None
                feedback_row.source_reference = None
                feedback_row.consent_id = None
                feedback_row.status = FeedbackStatus.ANONYMIZED.value
                feedback_row.creator_signal_reference = None
                point_rows = tuple(
                    await session.scalars(
                        select(MetricPointRow).where(
                            MetricPointRow.source_feedback_event_id == feedback_row.id,
                            MetricPointRow.included.is_(True),
                        )
                    )
                )
                for point_row in point_rows:
                    point_row.included = False
                    point_row.tombstoned_at = withdrawn_at
                    tombstones.append(
                        _new_tombstone(
                            workspace_id,
                            project_id,
                            feedback_row.id,
                            ArtifactKind.METRIC_POINT,
                            f"metric-point://{point_row.id}",
                            TombstoneAction.RECOMPUTE,
                            withdrawn_at,
                        )
                    )
                sample_rows = tuple(
                    await session.scalars(
                        select(ExperimentSampleRow).where(
                            ExperimentSampleRow.source_feedback_event_id == feedback_row.id,
                            ExperimentSampleRow.included.is_(True),
                        )
                    )
                )
                for sample_row in sample_rows:
                    sample_row.included = False
                    sample_row.tombstoned_at = withdrawn_at
                    tombstones.append(
                        _new_tombstone(
                            workspace_id,
                            project_id,
                            feedback_row.id,
                            ArtifactKind.EXPERIMENT_SAMPLE,
                            f"experiment-sample://{sample_row.id}",
                            TombstoneAction.EXCLUDE,
                            withdrawn_at,
                        )
                    )
                if creator_reference is not None:
                    tombstones.append(
                        _new_tombstone(
                            workspace_id,
                            project_id,
                            feedback_row.id,
                            ArtifactKind.CREATOR_SIGNAL,
                            creator_reference,
                            TombstoneAction.EXCLUDE,
                            withdrawn_at,
                        )
                    )
            session.add_all(_tombstone_row(item) for item in tombstones)
            await SqlAlchemyOutboxWriter(session).append(event)
            return WithdrawalResult(
                _consent(consent_row), tuple(row.id for row in feedback_rows), tuple(tombstones)
            )

    async def add_feedback(self, item: FeedbackEvent, event: EventEnvelope) -> FeedbackEvent:
        async with self._sessions.begin() as session:
            existing = await session.get(FeedbackEventRow, item.id)
            if existing is not None:
                return _feedback(existing)
            session.add(_feedback_row(item))
            await SqlAlchemyOutboxWriter(session).append(event)
        return item

    async def get_feedback(
        self, workspace_id: UUID, project_id: UUID, event_id: UUID
    ) -> FeedbackEvent | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(FeedbackEventRow).where(
                    FeedbackEventRow.workspace_id == workspace_id,
                    FeedbackEventRow.project_id == project_id,
                    FeedbackEventRow.id == event_id,
                )
            )
        return None if row is None else _feedback(row)

    async def add_metric_definition(self, item: MetricDefinition) -> MetricDefinition:
        async with self._sessions.begin() as session:
            existing = await session.get(MetricDefinitionRow, item.id)
            if existing is not None:
                return _definition(existing)
            session.add(_definition_row(item))
        return item

    async def add_metric_point(self, item: MetricPoint, event: EventEnvelope) -> MetricPoint:
        async with self._sessions.begin() as session:
            existing = await session.get(MetricPointRow, item.id)
            if existing is not None:
                return _point(existing)
            session.add(_point_row(item))
            await SqlAlchemyOutboxWriter(session).append(event)
        return item

    async def get_metric_point(
        self, workspace_id: UUID, project_id: UUID, point_id: UUID
    ) -> MetricPoint | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(MetricPointRow).where(
                    MetricPointRow.workspace_id == workspace_id,
                    MetricPointRow.project_id == project_id,
                    MetricPointRow.id == point_id,
                )
            )
        return None if row is None else _point(row)

    async def add_diagnostic(
        self, item: DiagnosticFinding, event: EventEnvelope
    ) -> DiagnosticFinding:
        async with self._sessions.begin() as session:
            existing = await session.get(DiagnosticFindingRow, item.id)
            if existing is not None:
                return _diagnostic(existing)
            session.add(_diagnostic_row(item))
            await SqlAlchemyOutboxWriter(session).append(event)
        return item

    async def get_diagnostic(
        self, workspace_id: UUID, project_id: UUID, finding_id: UUID
    ) -> DiagnosticFinding | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(DiagnosticFindingRow).where(
                    DiagnosticFindingRow.workspace_id == workspace_id,
                    DiagnosticFindingRow.project_id == project_id,
                    DiagnosticFindingRow.id == finding_id,
                )
            )
        return None if row is None else _diagnostic(row)

    async def add_experiment(
        self, item: Experiment, variants: tuple[Variant, ...], event: EventEnvelope
    ) -> tuple[Experiment, tuple[Variant, ...]]:
        async with self._sessions.begin() as session:
            existing = await session.get(ExperimentRow, item.id)
            if existing is not None:
                rows = tuple(
                    await session.scalars(
                        select(VariantRow)
                        .where(VariantRow.experiment_id == item.id)
                        .order_by(VariantRow.variant_key)
                    )
                )
                return _experiment(existing), tuple(_variant(row) for row in rows)
            session.add(_experiment_row(item))
            session.add_all(_variant_row(variant) for variant in variants)
            await SqlAlchemyOutboxWriter(session).append(event)
        return item, variants

    async def get_experiment(
        self, workspace_id: UUID, project_id: UUID, experiment_id: UUID
    ) -> tuple[Experiment, tuple[Variant, ...]] | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(ExperimentRow).where(
                    ExperimentRow.workspace_id == workspace_id,
                    ExperimentRow.project_id == project_id,
                    ExperimentRow.id == experiment_id,
                )
            )
            if row is None:
                return None
            variant_rows = tuple(
                await session.scalars(
                    select(VariantRow)
                    .where(VariantRow.experiment_id == experiment_id)
                    .order_by(VariantRow.variant_key)
                )
            )
        return _experiment(row), tuple(_variant(item) for item in variant_rows)

    async def transition_experiment(
        self,
        item: Experiment,
        expected_status: ExperimentStatus,
        event: EventEnvelope,
    ) -> Experiment:
        async with self._sessions.begin() as session:
            row = await session.scalar(
                select(ExperimentRow)
                .where(
                    ExperimentRow.workspace_id == item.workspace_id,
                    ExperimentRow.project_id == item.project_id,
                    ExperimentRow.id == item.id,
                )
                .with_for_update()
            )
            if row is None or row.status != expected_status.value:
                raise InvalidStateError("Experiment is unavailable or changed concurrently.")
            row.status = item.status.value
            row.result_code = item.result_code
            await SqlAlchemyOutboxWriter(session).append(event)
        return item

    async def add_sample(self, item: ExperimentSample, event: EventEnvelope) -> ExperimentSample:
        async with self._sessions.begin() as session:
            existing = await session.get(ExperimentSampleRow, item.id)
            if existing is not None:
                return _sample(existing)
            session.add(_sample_row(item))
            await SqlAlchemyOutboxWriter(session).append(event)
        return item


def _new_tombstone(  # noqa: PLR0913, PLR0917
    workspace_id: UUID,
    project_id: UUID,
    event_id: UUID,
    kind: ArtifactKind,
    reference: str,
    action: TombstoneAction,
    now: datetime,
) -> DerivedArtifactTombstone:
    return DerivedArtifactTombstone(
        uuid5(NAMESPACE_URL, f"accos:{event_id}:{kind.value}:{reference}"),
        workspace_id,
        project_id,
        event_id,
        kind,
        reference,
        action,
        "behavior-consent-withdrawn",
        now,
    )


def _consent_row(item: BehaviorConsent) -> BehaviorConsentRow:
    return BehaviorConsentRow(
        id=item.id,
        workspace_id=item.workspace_id,
        project_id=item.project_id,
        actor_id=item.actor_id,
        policy_version=item.policy_version,
        status=item.status.value,
        granted_at=item.granted_at,
        withdrawn_at=item.withdrawn_at,
    )


def _consent(row: BehaviorConsentRow) -> BehaviorConsent:
    return BehaviorConsent(
        row.id,
        row.workspace_id,
        row.project_id,
        row.actor_id,
        row.policy_version,
        ConsentStatus(row.status),
        row.granted_at,
        row.withdrawn_at,
    )


def _feedback_row(item: FeedbackEvent) -> FeedbackEventRow:
    return FeedbackEventRow(
        id=item.id,
        workspace_id=item.workspace_id,
        project_id=item.project_id,
        actor_id=item.actor_id,
        source=item.source.value,
        schema_version=item.schema_version,
        signal_code=item.signal_code,
        numeric_value=item.numeric_value,
        source_reference=item.source_reference,
        consent_id=item.consent_id,
        status=item.status.value,
        occurred_at=item.occurred_at,
        creator_signal_reference=item.creator_signal_reference,
    )


def _feedback(row: FeedbackEventRow) -> FeedbackEvent:
    return FeedbackEvent(
        row.id,
        row.workspace_id,
        row.project_id,
        row.actor_id,
        FeedbackSource(row.source),
        row.schema_version,
        row.signal_code,
        row.numeric_value,
        row.source_reference,
        row.consent_id,
        FeedbackStatus(row.status),
        row.occurred_at,
        row.creator_signal_reference,
    )


def _definition_row(item: MetricDefinition) -> MetricDefinitionRow:
    return MetricDefinitionRow(
        id=item.id,
        workspace_id=item.workspace_id,
        project_id=item.project_id,
        name=item.name,
        version=item.version,
        unit=item.unit,
        dimensions=[
            {"key": dimension.key, "allowed_values": list(dimension.allowed_values)}
            for dimension in item.dimensions
        ],
        retention_days=item.retention_days,
        sensitivity=item.sensitivity.value,
        created_by=item.created_by,
        created_at=item.created_at,
    )


def _definition(row: MetricDefinitionRow) -> MetricDefinition:
    return MetricDefinition(
        row.id,
        row.workspace_id,
        row.project_id,
        row.name,
        row.version,
        row.unit,
        tuple(
            MetricDimension(
                str(item["key"]),
                tuple(str(value) for value in cast("list[object]", item["allowed_values"])),
            )
            for item in row.dimensions
        ),
        row.retention_days,
        MetricSensitivity(row.sensitivity),
        row.created_by,
        row.created_at,
    )


def _point_row(item: MetricPoint) -> MetricPointRow:
    return MetricPointRow(
        id=item.id,
        workspace_id=item.workspace_id,
        project_id=item.project_id,
        metric_definition_id=item.metric_definition_id,
        metric_name=item.metric_name,
        value=item.value,
        dimensions=[list(value) for value in item.dimensions],
        observed_at=item.observed_at,
        source_reference=item.source_reference,
        source_feedback_event_id=item.source_feedback_event_id,
        included=item.included,
        tombstoned_at=item.tombstoned_at,
    )


def _point(row: MetricPointRow) -> MetricPoint:
    return MetricPoint(
        row.id,
        row.workspace_id,
        row.project_id,
        row.metric_definition_id,
        row.metric_name,
        row.value,
        tuple((str(value[0]), str(value[1])) for value in row.dimensions),
        row.observed_at,
        row.source_reference,
        row.source_feedback_event_id,
        row.included,
        row.tombstoned_at,
    )


def _diagnostic_row(item: DiagnosticFinding) -> DiagnosticFindingRow:
    return DiagnosticFindingRow(
        id=item.id,
        workspace_id=item.workspace_id,
        project_id=item.project_id,
        metric_point_id=item.metric_point_id,
        rule_key=item.rule_key,
        rule_version=item.rule_version,
        finding_code=item.finding_code,
        severity=item.severity.value,
        observed_value=item.observed_value,
        threshold_value=item.threshold_value,
        created_at=item.created_at,
    )


def _diagnostic(row: DiagnosticFindingRow) -> DiagnosticFinding:
    return DiagnosticFinding(
        row.id,
        row.workspace_id,
        row.project_id,
        row.metric_point_id,
        row.rule_key,
        row.rule_version,
        row.finding_code,
        DiagnosticSeverity(row.severity),
        row.observed_value,
        row.threshold_value,
        row.created_at,
    )


def _experiment_row(item: Experiment) -> ExperimentRow:
    return ExperimentRow(
        id=item.id,
        workspace_id=item.workspace_id,
        project_id=item.project_id,
        experiment_key=item.experiment_key,
        protocol_version=item.protocol_version,
        hypothesis_code=item.hypothesis_code,
        primary_metric_name=item.primary_metric_name,
        sample_scope=item.sample_scope,
        starts_at=item.starts_at,
        ends_at=item.ends_at,
        stop_condition_codes=list(item.stop_condition_codes),
        status=item.status.value,
        created_by=item.created_by,
        created_at=item.created_at,
        result_code=item.result_code,
    )


def _experiment(row: ExperimentRow) -> Experiment:
    return Experiment(
        row.id,
        row.workspace_id,
        row.project_id,
        row.experiment_key,
        row.protocol_version,
        row.hypothesis_code,
        row.primary_metric_name,
        row.sample_scope,
        row.starts_at,
        row.ends_at,
        tuple(row.stop_condition_codes),
        ExperimentStatus(row.status),
        row.created_by,
        row.created_at,
        row.result_code,
    )


def _variant_row(item: Variant) -> VariantRow:
    return VariantRow(
        id=item.id,
        experiment_id=item.experiment_id,
        variant_key=item.variant_key,
        configuration_reference=item.configuration_reference,
    )


def _variant(row: VariantRow) -> Variant:
    return Variant(row.id, row.experiment_id, row.variant_key, row.configuration_reference)


def _sample_row(item: ExperimentSample) -> ExperimentSampleRow:
    return ExperimentSampleRow(
        id=item.id,
        workspace_id=item.workspace_id,
        project_id=item.project_id,
        experiment_id=item.experiment_id,
        variant_id=item.variant_id,
        metric_point_id=item.metric_point_id,
        source_feedback_event_id=item.source_feedback_event_id,
        observed_at=item.observed_at,
        included=item.included,
        tombstoned_at=item.tombstoned_at,
    )


def _sample(row: ExperimentSampleRow) -> ExperimentSample:
    return ExperimentSample(
        row.id,
        row.workspace_id,
        row.project_id,
        row.experiment_id,
        row.variant_id,
        row.metric_point_id,
        row.source_feedback_event_id,
        row.observed_at,
        row.included,
        row.tombstoned_at,
    )


def _tombstone_row(item: DerivedArtifactTombstone) -> TombstoneRow:
    return TombstoneRow(
        id=item.id,
        workspace_id=item.workspace_id,
        project_id=item.project_id,
        source_feedback_event_id=item.source_feedback_event_id,
        artifact_kind=item.artifact_kind.value,
        artifact_reference=item.artifact_reference,
        action=item.action.value,
        reason_code=item.reason_code,
        created_at=item.created_at,
    )


MODEL_REGISTRY = (
    BehaviorConsentRow,
    FeedbackEventRow,
    MetricDefinitionRow,
    MetricPointRow,
    DiagnosticFindingRow,
    ExperimentRow,
    VariantRow,
    ExperimentSampleRow,
    TombstoneRow,
)
