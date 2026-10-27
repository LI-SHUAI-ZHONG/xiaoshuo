"""Deterministic structural checks and a fail-honest validator registry."""

from __future__ import annotations

from collections import defaultdict
from enum import StrEnum
from typing import TYPE_CHECKING

from accos.modules.consistency.domain import (
    CanonLevel,
    FindingDraft,
    FindingSeverity,
    FindingType,
    ValidationStatus,
    ValidatorReport,
)

if TYPE_CHECKING:
    from accos.modules.consistency.domain import ValidationBundle
    from accos.modules.consistency.ports import ValidatorPort


class ValidatorKind(StrEnum):
    CHARACTER = "character"
    TIMELINE = "timeline"
    WORLD_RULE = "world_rule"
    PLOT_DEPENDENCY = "plot_dependency"
    THEME_ALIGNMENT = "theme_alignment"


class StructuralValidator:
    key = "structural"
    version = "1.0.0"

    async def validate(self, evidence: ValidationBundle) -> ValidatorReport:
        findings = (
            *_required_findings(evidence),
            *_reference_findings(evidence),
            *_timeline_findings(evidence),
            *_mutex_findings(evidence),
            *_version_findings(evidence),
            *_canon_findings(evidence),
            *_dependency_findings(evidence),
        )
        return ValidatorReport(
            self.key,
            self.version,
            ValidationStatus.FINDINGS if findings else ValidationStatus.PASSED,
            findings,
        )


class NullSemanticValidator:
    version = "0.0.0"

    def __init__(self, kind: ValidatorKind) -> None:
        self.kind = kind
        self.key = kind.value

    async def validate(self, evidence: ValidationBundle) -> ValidatorReport:  # noqa: ARG002
        return ValidatorReport(self.key, self.version, ValidationStatus.NOT_CONFIGURED)


class ValidatorRegistry:
    """Explicit registry; a missing checker is NOT_CONFIGURED, never passed."""

    def __init__(self, validators: tuple[ValidatorPort, ...] = ()) -> None:
        self._validators = {item.key: item for item in validators}

    def register(self, validator: ValidatorPort) -> None:
        if validator.key in self._validators:
            raise ValueError(f"validator already registered: {validator.key}")
        self._validators[validator.key] = validator

    def not_run(self, key: str, version: str = "0.0.0") -> ValidatorReport:
        return ValidatorReport(key, version, ValidationStatus.NOT_RUN)

    async def run(self, key: str, evidence: ValidationBundle) -> ValidatorReport:
        validator = self._validators.get(key)
        if validator is None:
            return ValidatorReport(key, "0.0.0", ValidationStatus.NOT_CONFIGURED)
        try:
            return await validator.validate(evidence)
        except Exception:  # noqa: BLE001 - checker details must not cross the boundary.
            return ValidatorReport(
                validator.key,
                validator.version,
                ValidationStatus.RUN_FAILED,
                error_code="validator_execution_failed",
            )


def default_validator_registry() -> ValidatorRegistry:
    return ValidatorRegistry(
        (
            StructuralValidator(),
            *(NullSemanticValidator(kind) for kind in ValidatorKind),
        )
    )


def _finding(
    finding_type: FindingType,
    references: tuple[str, ...],
    message_code: str,
    severity: FindingSeverity = FindingSeverity.ERROR,
) -> FindingDraft:
    return FindingDraft(finding_type, severity, references, message_code)


def _required_findings(evidence: ValidationBundle) -> tuple[FindingDraft, ...]:
    return tuple(
        _finding(
            FindingType.REQUIRED_FIELD,
            (item.evidence_reference,),
            "required_field_missing",
        )
        for item in evidence.required_fields
        if not item.present
    )


def _reference_findings(evidence: ValidationBundle) -> tuple[FindingDraft, ...]:
    return tuple(
        _finding(
            FindingType.INVALID_REFERENCE,
            (item.evidence_reference,),
            "reference_unavailable",
        )
        for item in evidence.references
        if not item.exists
    )


def _timeline_findings(evidence: ValidationBundle) -> tuple[FindingDraft, ...]:
    return tuple(
        _finding(
            FindingType.TIME_ORDER,
            (item.predecessor_reference or "", item.event_reference),
            "timeline_precedes_dependency",
        )
        for item in evidence.timeline
        if item.predecessor_reference is not None
        and item.predecessor_occurred_at is not None
        and item.occurred_at < item.predecessor_occurred_at
    )


def _mutex_findings(evidence: ValidationBundle) -> tuple[FindingDraft, ...]:
    current_states: dict[tuple[str, str], set[str]] = defaultdict(set)
    for item in evidence.entity_states:
        if item.current:
            current_states[(item.entity_reference, item.mutex_group)].add(item.state_code)
    return tuple(
        _finding(
            FindingType.MUTEX_STATE,
            (entity_reference,),
            f"mutex_state:{mutex_group}",
        )
        for (entity_reference, mutex_group), states in current_states.items()
        if len(states) > 1
    )


def _version_findings(evidence: ValidationBundle) -> tuple[FindingDraft, ...]:
    return tuple(
        _finding(
            FindingType.VERSION_CONFLICT,
            (item.evidence_reference,),
            "evidence_version_changed",
        )
        for item in evidence.versions
        if item.expected_version != item.current_version
    )


def _canon_findings(evidence: ValidationBundle) -> tuple[FindingDraft, ...]:
    return tuple(
        _finding(
            FindingType.PROTECTED_CANON,
            (item.canon_reference,),
            "level_1_change_not_authorized",
            FindingSeverity.BLOCKER,
        )
        for item in evidence.canon_changes
        if item.level is CanonLevel.LEVEL_1
        and item.modifies_current
        and not item.explicitly_authorized
    )


def _dependency_findings(evidence: ValidationBundle) -> tuple[FindingDraft, ...]:
    return tuple(
        _finding(
            FindingType.UNRESOLVED_DEPENDENCY,
            (item.source_reference, item.target_reference),
            "dependency_unresolved",
        )
        for item in evidence.dependencies
        if not item.resolved
    )
