"""Deterministic validation and hashing for versioned Workflow DAGs."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, assert_never

from accos.modules.workflows.domain import (
    ConditionOperator,
    StepRunStatus,
    WorkflowDefinition,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from accos.modules.workflows.domain import StepDefinition, StepInputManifest


def topological_steps(definition: WorkflowDefinition) -> tuple[StepDefinition, ...]:
    """Return a stable topological order, using position only as a tie breaker."""
    remaining = {step.key: step for step in definition.steps}
    resolved: set[str] = set()
    ordered: list[StepDefinition] = []
    while remaining:
        ready = sorted(
            (
                step
                for step in remaining.values()
                if set(definition.dependencies_for(step)).issubset(resolved)
            ),
            key=lambda step: (step.position, step.key),
        )
        if not ready:
            raise ValueError("workflow definition must be acyclic")
        for step in ready:
            ordered.append(step)
            resolved.add(step.key)
            remaining.pop(step.key)
    return tuple(ordered)


def ready_step_keys(
    definition: WorkflowDefinition,
    statuses: Mapping[str, StepRunStatus],
) -> tuple[str, ...]:
    """Return unmaterialized nodes whose dependencies have settled successfully."""
    satisfied = {StepRunStatus.SUCCEEDED, StepRunStatus.SKIPPED}
    return tuple(
        step.key
        for step in topological_steps(definition)
        if step.key not in statuses
        and all(statuses.get(key) in satisfied for key in definition.dependencies_for(step))
    )


def condition_matches(
    step: StepDefinition,
    *,
    dependency_statuses: Mapping[str, StepRunStatus],
    dependency_outputs: Mapping[str, str | None],
) -> bool:
    """Evaluate the fixed metadata-only condition language."""
    condition = step.condition
    if condition.operator is ConditionOperator.ALWAYS:
        return True
    source = condition.source_step_key
    if source is None:
        return False
    if condition.operator is ConditionOperator.REFERENCE_PRESENT:
        return dependency_outputs.get(source) is not None
    if condition.operator is ConditionOperator.STATUS_EQUALS:
        status = dependency_statuses.get(source)
        return status is not None and status.value == condition.expected_value
    if condition.operator is ConditionOperator.OUTPUT_REFERENCE_EQUALS:
        return dependency_outputs.get(source) == condition.expected_value
    assert_never(condition.operator)


def definition_checksum(definition: WorkflowDefinition) -> str:
    """Hash the behavior-bearing definition fields for immutable publication."""
    payload = {
        "name": definition.name,
        "version": definition.version,
        "graph_version": definition.graph_version,
        "steps": [
            {
                "id": str(step.id),
                "key": step.key,
                "position": step.position,
                "kind": step.kind.value,
                "executor_key": step.executor_key,
                "depends_on": definition.dependencies_for(step),
                "input_schema": step.input_schema,
                "output_schema": step.output_schema,
                "requirements": [
                    {
                        "key": item.key,
                        "artifact_type": item.artifact_type,
                        "scope": item.scope,
                        "branch": item.branch,
                        "accepted_required": item.accepted_required,
                        "min_schema": item.min_schema,
                        "mandatory": item.mandatory,
                        "freshness": item.freshness.value,
                        "max_age_seconds": item.max_age_seconds,
                    }
                    for item in step.requirements
                ],
                "condition": {
                    "operator": step.condition.operator.value,
                    "source_step_key": step.condition.source_step_key,
                    "expected_value": step.condition.expected_value,
                },
                "timeout_seconds": step.timeout_seconds,
                "retry": {
                    "max_attempts": step.retry_policy.max_attempts,
                    "initial_delay_seconds": step.retry_policy.initial_delay_seconds,
                    "maximum_delay_seconds": step.retry_policy.maximum_delay_seconds,
                    "multiplier": step.retry_policy.multiplier,
                },
                "budget_limit_microusd": step.budget_limit_microusd,
                "budget_reservation_required": step.budget_reservation_required,
                "approval_policy_ref": step.approval_policy_ref,
                "max_iterations": step.max_iterations,
                "compensation_hook": step.compensation_hook,
                "external_side_effect": step.external_side_effect,
                "operation_key_template": step.operation_key_template,
            }
            for step in definition.steps
        ],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def manifest_digest(manifest: StepInputManifest) -> str:
    """Recompute the frozen manifest digest independently of ORM identity."""
    payload = {
        "workflow_run_id": str(manifest.workflow_run_id),
        "step_run_id": str(manifest.step_run_id),
        "definition_id": str(manifest.definition_id),
        "definition_version": manifest.definition_version,
        "step_definition_id": str(manifest.step_definition_id),
        "executor_key": manifest.executor_key,
        "resolved_inputs": [
            {
                "requirement_key": item.requirement_key,
                "reference": item.reference,
                "revision": item.revision,
                "content_hash": item.content_hash,
                "schema_version": item.schema_version,
                "status": item.status.value,
                "grant_version": item.grant_version,
                "consent_version": item.consent_version,
            }
            for item in manifest.resolved_inputs
        ],
        "prompt_pin": manifest.prompt_pin,
        "model_pin": manifest.model_pin,
        "policy_pin": manifest.policy_pin,
        "permission_version": manifest.permission_version,
        "grant_version": manifest.grant_version,
        "consent_version": manifest.consent_version,
        "budget_reservation_ref": manifest.budget_reservation_ref,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
