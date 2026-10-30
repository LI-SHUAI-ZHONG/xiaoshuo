from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest

from accos.adapters.models import (
    FakeModelBehavior,
    FakeModelProvider,
    FakeModelScenario,
    InMemoryUsageLedger,
    MappingSecretProvider,
    NullModelProvider,
    NullSecretProvider,
)
from accos.adapters.tools import (
    FakeToolBehavior,
    FakeToolExecutor,
    FakeToolScenario,
    InMemoryToolCallLedger,
    RepositoryPluginLoader,
)
from accos.kernel.errors import PermissionDeniedError
from accos.kernel.ids import CorrelationIds
from accos.kernel.security import ActorKind, SecurityContext
from accos.modules.identity.public import (
    AuditEvent,
    AuthorizationService,
    Permission,
)
from accos.modules.models import public as model_public
from accos.modules.models.public import (
    MODEL_PROTOCOL_VERSION,
    PROMPT_POLICY_METADATA_PROTOCOL_VERSION,
    MetadataKind,
    MetadataStatus,
    ModelCallStatus,
    ModelCapability,
    ModelErrorCode,
    ModelGateway,
    ModelGatewayError,
    ModelPolicy,
    ModelRegistry,
    ModelRequest,
    PromptPolicyMetadata,
    PromptPolicyRegistry,
    ProviderHealthState,
    ProviderResult,
    UsageRecord,
)
from accos.modules.tools import public as tool_public
from accos.modules.tools.public import (
    PLUGIN_MANIFEST_PROTOCOL_VERSION,
    TOOL_PROTOCOL_VERSION,
    PluginManifest,
    PluginTrustStatus,
    ToolAuditPolicy,
    ToolCallStatus,
    ToolDescriptor,
    ToolErrorCode,
    ToolGateway,
    ToolGatewayError,
    ToolGrant,
    ToolRegistry,
    ToolRequest,
    ToolResult,
)
from accos.modules.workflows.public import (
    FrameworkSmokeExecutor,
    GatewayWorkflowExecutor,
    StepExecution,
    StepKind,
)

if TYPE_CHECKING:
    from accos.modules.models.public import ModelProvider

NOW = datetime(2026, 9, 5, tzinfo=UTC)
ACTOR_ID = UUID("10000000-0000-4000-8000-000000000001")
WORKSPACE_ID = UUID("20000000-0000-4000-8000-000000000001")
PROJECT_ID = UUID("30000000-0000-4000-8000-000000000001")
WORKFLOW_ID = UUID("40000000-0000-4000-8000-000000000001")
TASK_ID = UUID("50000000-0000-4000-8000-000000000001")
CORRELATION_ID = UUID("60000000-0000-4000-8000-000000000001")


@dataclass(slots=True)
class MutableClock:
    value: datetime = NOW

    def now(self) -> datetime:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += timedelta(seconds=seconds)


class MemoryAudit:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def append(self, event: AuditEvent) -> None:
        self.events.append(event)


def context(*, permissions: frozenset[str] | None = None) -> SecurityContext:
    return SecurityContext(
        ACTOR_ID,
        ActorKind.USER,
        WORKSPACE_ID,
        permissions or frozenset({Permission.MODEL_RUN.value, Permission.TOOL_RUN.value}),
        "fixture-policy-v1",
        CorrelationIds(str(CORRELATION_ID), str(CORRELATION_ID), str(TASK_ID)),
        PROJECT_ID,
    )


def model_request(
    key: str = "fixture-model-call",
    *,
    capability: ModelCapability = ModelCapability.TEXT,
    max_tokens: int = 16,
    metadata: PromptPolicyMetadata | None = None,
) -> ModelRequest:
    return ModelRequest(
        capability,
        "fixture-token://model-input",
        max_tokens,
        key,
        WORKFLOW_ID,
        TASK_ID,
        metadata,
    )


def model_policy(**updates: object) -> ModelPolicy:
    values: dict[str, object] = {
        "allowed_provider_ids": ("fake-primary", "fake-backup"),
        "primary_provider_id": "fake-primary",
        "backup_provider_ids": ("fake-backup",),
        "timeout_seconds": 0.2,
        "retries_per_provider": 0,
        "retry_backoff_seconds": 0,
        "total_attempt_limit": 4,
        "circuit_failure_threshold": 2,
        "circuit_cooldown_seconds": 1,
        "concurrency_limit": 1,
        "workspace_token_budget": 100,
        "task_token_budget": 50,
        "workspace_call_limit": 10,
        "task_call_limit": 5,
        "max_tokens_per_call": 20,
    }
    values.update(updates)
    return ModelPolicy(**values)  # type: ignore[arg-type]


def build_model_gateway(
    providers: tuple[ModelProvider, ...],
    *,
    policy: ModelPolicy | None = None,
    ledger: InMemoryUsageLedger | None = None,
    clock: MutableClock | None = None,
    audit: MemoryAudit | None = None,
) -> tuple[ModelGateway, InMemoryUsageLedger, MutableClock, MemoryAudit]:
    registry = ModelRegistry()
    for provider in providers:
        registry.register(provider)
    selected_ledger = ledger or InMemoryUsageLedger()
    selected_clock = clock or MutableClock()
    selected_audit = audit or MemoryAudit()
    gateway = ModelGateway(
        registry,
        selected_ledger,
        AuthorizationService(selected_audit, selected_clock),
        selected_clock,
        policy or model_policy(),
    )
    return gateway, selected_ledger, selected_clock, selected_audit


def test_model_values_metadata_registry_and_secret_boundary() -> None:
    metadata = PromptPolicyMetadata(
        "fixture-policy", MetadataKind.POLICY, "1.0.0", "a" * 64, MetadataStatus.ACTIVE
    )
    registry = PromptPolicyRegistry()
    registry.register(metadata)
    registry.register(metadata)
    assert registry.get("fixture-policy", "1.0.0") is metadata
    assert registry.active("fixture-policy") is metadata
    assert registry.active("missing") is None
    assert model_public.ModelCapability is ModelCapability
    assert model_public.ModelResponse is not None
    assert MODEL_PROTOCOL_VERSION == "models.v1"
    assert PROMPT_POLICY_METADATA_PROTOCOL_VERSION == "prompt-policy-metadata.v1"

    with pytest.raises(ValueError, match="metadata id"):
        PromptPolicyMetadata("", MetadataKind.PROMPT, "1.0.0", "a" * 64, MetadataStatus.DRAFT)
    with pytest.raises(ValueError, match=r"major\.minor\.patch"):
        PromptPolicyMetadata("fixture", MetadataKind.PROMPT, "v1", "a" * 64, MetadataStatus.DRAFT)
    with pytest.raises(ValueError, match="checksum"):
        PromptPolicyMetadata("fixture", MetadataKind.PROMPT, "1.0.0", "bad", MetadataStatus.DRAFT)
    with pytest.raises(ValueError, match="immutable"):
        registry.register(
            PromptPolicyMetadata(
                "fixture-policy",
                MetadataKind.PROMPT,
                "1.0.0",
                "b" * 64,
                MetadataStatus.ACTIVE,
            )
        )
    registry.register(
        PromptPolicyMetadata(
            "fixture-policy", MetadataKind.POLICY, "2.0.0", "c" * 64, MetadataStatus.ACTIVE
        )
    )
    with pytest.raises(ValueError, match="multiple active"):
        registry.active("fixture-policy")

    with pytest.raises(ValueError, match="opaque reference"):
        model_request().__class__(
            ModelCapability.TEXT, "raw input", 1, "fixture", WORKFLOW_ID, TASK_ID
        )
    with pytest.raises(ValueError, match="positive"):
        model_request(max_tokens=0)
    result = ProviderResult("model-output://fixture/result", 2, 3)
    assert result.total_tokens == 5
    with pytest.raises(ValueError, match="output"):
        ProviderResult("raw", 0, 0)
    with pytest.raises(ValueError, match="negative"):
        ProviderResult("model-output://fixture/result", -1, 0)

    secrets = MappingSecretProvider({"fixture": "credential-sentinel-value"})
    assert asyncio.run(secrets.credential_for("fixture")) == "credential-sentinel-value"
    assert asyncio.run(secrets.credential_for("missing")) is None
    assert asyncio.run(NullSecretProvider().credential_for("fixture")) is None


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"allowed_provider_ids": ()}, "allowlist"),
        ({"backup_provider_ids": ("fake-primary",)}, "unique"),
        ({"backup_provider_ids": ("not-allowed",)}, "allowlist"),
        ({"timeout_seconds": 0}, "resilience"),
        ({"retries_per_provider": -1}, "resilience"),
        ({"workspace_token_budget": 0}, "budgets"),
    ],
)
def test_model_policy_rejects_unbounded_or_implicit_routes(
    updates: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        model_policy(**updates)


def test_fake_model_success_delay_registry_and_provider_contract() -> None:
    delayed = FakeModelProvider(
        "fake-primary",
        behaviors={"fixture-model-call": FakeModelBehavior(FakeModelScenario.DELAY, 0.001, 2, 3)},
    )
    backup = FakeModelProvider("fake-backup")
    gateway, ledger, _clock, audit = build_model_gateway((delayed, backup))
    response = asyncio.run(gateway.invoke(context(), model_request()))

    assert response.provider_id == "fake-primary"
    assert response.total_tokens == 5
    assert response.call_id == ledger.records[0].id
    assert ledger.records[0].status is ModelCallStatus.SUCCEEDED
    assert asyncio.run(ledger.totals(WORKSPACE_ID, TASK_ID)).task_tokens == 5
    assert asyncio.run(ledger.for_workflow(WORKSPACE_ID, WORKFLOW_ID)) == tuple(ledger.records)
    assert asyncio.run(ledger.for_workflow(uuid4(), WORKFLOW_ID)) == ()
    assert audit.events[-1].action == Permission.MODEL_RUN.value
    assert gateway.health()[0].state is ProviderHealthState.AVAILABLE

    registry = ModelRegistry()
    registry.register(delayed)
    assert registry.capabilities()["fake-primary"] == {
        ModelCapability.TEXT,
        ModelCapability.EMBEDDING,
    }
    assert registry.route(ModelCapability.IMAGE, model_policy()) == ()
    with pytest.raises(ValueError, match="unique"):
        registry.register(delayed)
    with pytest.raises(ValueError, match="required"):
        FakeModelProvider("")
    with pytest.raises(ValueError, match="negative"):
        FakeModelBehavior(delay_seconds=-1)


def test_model_retry_fallback_and_shared_attempt_budget() -> None:
    primary = FakeModelProvider(
        "fake-primary", default_behavior=FakeModelBehavior(FakeModelScenario.FAILURE)
    )
    backup = FakeModelProvider("fake-backup")
    gateway, ledger, _clock, _audit = build_model_gateway(
        (primary, backup), policy=model_policy(retries_per_provider=1, circuit_failure_threshold=9)
    )
    response = asyncio.run(gateway.invoke(context(), model_request()))
    assert response.provider_id == "fake-backup"
    assert response.attempt == 3
    assert [record.status for record in ledger.records] == [
        ModelCallStatus.FAILED,
        ModelCallStatus.FAILED,
        ModelCallStatus.SUCCEEDED,
    ]
    totals = asyncio.run(ledger.totals(WORKSPACE_ID, TASK_ID))
    assert totals.task_calls == 3

    limited, limited_ledger, _clock, _audit = build_model_gateway(
        (primary, backup),
        policy=model_policy(
            retries_per_provider=2,
            total_attempt_limit=1,
            circuit_failure_threshold=9,
        ),
    )
    with pytest.raises(ModelGatewayError) as captured:
        asyncio.run(limited.invoke(context(), model_request("fixture-attempt-budget")))
    assert captured.value.code is ModelErrorCode.BUDGET_EXHAUSTED
    assert limited_ledger.records[-1].status is ModelCallStatus.BUDGET_DENIED


@pytest.mark.parametrize(
    ("scenario", "expected_status", "expected_code"),
    [
        (FakeModelScenario.RATE_LIMITED, ModelCallStatus.RATE_LIMITED, ModelErrorCode.RATE_LIMITED),
        (FakeModelScenario.FAILURE, ModelCallStatus.FAILED, ModelErrorCode.PROVIDER_FAILED),
        (FakeModelScenario.TIMEOUT, ModelCallStatus.TIMED_OUT, ModelErrorCode.TIMED_OUT),
    ],
)
def test_model_failure_modes_are_stable_and_audited(
    scenario: FakeModelScenario,
    expected_status: ModelCallStatus,
    expected_code: ModelErrorCode,
) -> None:
    primary = FakeModelProvider(
        "fake-primary", default_behavior=FakeModelBehavior(scenario, delay_seconds=0)
    )
    gateway, ledger, _clock, _audit = build_model_gateway(
        (primary,),
        policy=model_policy(
            allowed_provider_ids=("fake-primary",),
            backup_provider_ids=(),
            circuit_failure_threshold=2,
        ),
    )
    with pytest.raises(ModelGatewayError) as captured:
        asyncio.run(gateway.invoke(context(), model_request()))
    assert captured.value.code is expected_code
    assert ledger.records[-1].status is expected_status
    assert gateway.health()[0].state is ProviderHealthState.DEGRADED


def test_model_circuit_cooldown_null_provider_and_no_configuration() -> None:
    clock = MutableClock()
    failing = FakeModelProvider(
        "fake-primary", default_behavior=FakeModelBehavior(FakeModelScenario.FAILURE)
    )
    gateway, ledger, _clock, _audit = build_model_gateway(
        (failing,),
        clock=clock,
        policy=model_policy(
            allowed_provider_ids=("fake-primary",),
            backup_provider_ids=(),
            circuit_failure_threshold=1,
        ),
    )
    with pytest.raises(ModelGatewayError):
        asyncio.run(gateway.invoke(context(), model_request("fixture-circuit-1")))
    assert gateway.health()[0].state is ProviderHealthState.OPEN
    with pytest.raises(ModelGatewayError) as open_error:
        asyncio.run(gateway.invoke(context(), model_request("fixture-circuit-2")))
    assert open_error.value.code is ModelErrorCode.CIRCUIT_OPEN
    assert ledger.records[-1].status is ModelCallStatus.CIRCUIT_OPEN
    assert not ledger.records[-1].attempted
    clock.advance(2)
    with pytest.raises(ModelGatewayError) as after_cooldown:
        asyncio.run(gateway.invoke(context(), model_request("fixture-circuit-3")))
    assert after_cooldown.value.code is ModelErrorCode.PROVIDER_FAILED

    null = NullModelProvider("fake-primary", capabilities=frozenset({ModelCapability.TEXT}))
    null_gateway, _ledger, _clock, _audit = build_model_gateway(
        (null,),
        policy=model_policy(
            allowed_provider_ids=("fake-primary",),
            backup_provider_ids=(),
            circuit_failure_threshold=2,
        ),
    )
    with pytest.raises(ModelGatewayError) as null_error:
        asyncio.run(null_gateway.invoke(context(), model_request()))
    assert null_error.value.code is ModelErrorCode.NOT_CONFIGURED
    assert null_gateway.health()[0].state is ProviderHealthState.NOT_CONFIGURED
    assert null.capabilities == {ModelCapability.TEXT}

    no_route, no_route_ledger, _clock, _audit = build_model_gateway(
        (FakeModelProvider("fake-primary"),),
        policy=model_policy(allowed_provider_ids=("fake-primary",), backup_provider_ids=()),
    )
    with pytest.raises(ModelGatewayError) as missing:
        asyncio.run(no_route.invoke(context(), model_request(capability=ModelCapability.IMAGE)))
    assert missing.value.code is ModelErrorCode.NOT_CONFIGURED
    assert no_route_ledger.records[-1].status is ModelCallStatus.NOT_CONFIGURED


def test_model_budget_metadata_response_and_authorization_guards() -> None:
    provider = FakeModelProvider("fake-primary")
    policy = model_policy(
        allowed_provider_ids=("fake-primary",), backup_provider_ids=(), max_tokens_per_call=5
    )
    gateway, ledger, _clock, _audit = build_model_gateway((provider,), policy=policy)
    with pytest.raises(ModelGatewayError) as too_large:
        asyncio.run(gateway.invoke(context(), model_request(max_tokens=6)))
    assert too_large.value.code is ModelErrorCode.BUDGET_EXHAUSTED
    assert not ledger.records[-1].attempted

    ledger.records.append(
        UsageRecord(
            uuid4(),
            WORKSPACE_ID,
            PROJECT_ID,
            WORKFLOW_ID,
            TASK_ID,
            ACTOR_ID,
            CORRELATION_ID,
            "fixture-existing",
            ModelCapability.TEXT,
            "fake-primary",
            ModelCallStatus.SUCCEEDED,
            None,
            True,
            1,
            2,
            3,
            NOW,
            NOW,
        )
    )
    exhausted_policy = model_policy(
        allowed_provider_ids=("fake-primary",),
        backup_provider_ids=(),
        task_call_limit=1,
    )
    exhausted = build_model_gateway((provider,), policy=exhausted_policy, ledger=ledger)[0]
    with pytest.raises(ModelGatewayError) as budget:
        asyncio.run(exhausted.invoke(context(), model_request("fixture-budget")))
    assert budget.value.code is ModelErrorCode.BUDGET_EXHAUSTED

    inactive = PromptPolicyMetadata(
        "fixture-prompt", MetadataKind.PROMPT, "1.0.0", "d" * 64, MetadataStatus.DRAFT
    )
    with pytest.raises(ValueError, match="must be active"):
        asyncio.run(gateway.invoke(context(), model_request(metadata=inactive, max_tokens=5)))

    unauthorized_gateway, unauthorized_ledger, _clock, unauthorized_audit = build_model_gateway(
        (provider,), policy=policy
    )
    with pytest.raises(PermissionDeniedError):
        asyncio.run(
            unauthorized_gateway.invoke(
                context(permissions=frozenset({Permission.TOOL_RUN.value})),
                model_request(max_tokens=5),
            )
        )
    assert unauthorized_ledger.records == []
    assert unauthorized_audit.events[-1].result == "denied"

    invalid = FakeModelProvider(
        "fake-primary", default_behavior=FakeModelBehavior(input_tokens=10, output_tokens=10)
    )
    invalid_gateway = build_model_gateway((invalid,), policy=policy)[0]
    with pytest.raises(ModelGatewayError) as invalid_response:
        asyncio.run(invalid_gateway.invoke(context(), model_request(max_tokens=5)))
    assert invalid_response.value.code is ModelErrorCode.INVALID_RESPONSE


class ConcurrentProvider:
    provider_id = "fake-primary"
    capabilities = frozenset({ModelCapability.TEXT})

    def __init__(self) -> None:
        self.active = 0
        self.maximum = 0

    async def invoke(self, request: ModelRequest) -> ProviderResult:
        del request
        self.active += 1
        self.maximum = max(self.maximum, self.active)
        try:
            await asyncio.sleep(0.005)
            return ProviderResult("model-output://concurrency/result", 1, 1)
        finally:
            self.active -= 1


def test_model_concurrency_limit_serializes_provider_calls() -> None:
    provider = ConcurrentProvider()
    gateway = build_model_gateway(
        (provider,),
        policy=model_policy(
            allowed_provider_ids=("fake-primary",),
            backup_provider_ids=(),
            timeout_seconds=0.1,
            concurrency_limit=1,
        ),
    )[0]

    async def exercise() -> None:
        await asyncio.gather(
            gateway.invoke(context(), model_request("fixture-concurrent-1")),
            gateway.invoke(context(), model_request("fixture-concurrent-2")),
        )

    asyncio.run(exercise())
    assert provider.maximum == 1


def tool_descriptor(**updates: object) -> ToolDescriptor:
    values: dict[str, object] = {
        "tool_id": "fixture.reference",
        "version": "1.0.0",
        "capabilities": ("reference",),
        "input_schema": {
            "type": "object",
            "properties": {"reference": {"type": "string"}},
            "required": ["reference"],
            "additionalProperties": False,
        },
        "output_schema": {
            "type": "object",
            "properties": {"reference": {"type": "string"}},
            "required": ["reference"],
            "additionalProperties": False,
        },
        "required_permissions": frozenset({Permission.TOOL_RUN.value}),
        "timeout_seconds": 0.02,
        "audit_policy": ToolAuditPolicy.METADATA,
    }
    values.update(updates)
    return ToolDescriptor(**values)  # type: ignore[arg-type]


def tool_request(
    key: str = "fixture-tool-call",
    *,
    input_data: dict[str, object] | None = None,
    **updates: object,
) -> ToolRequest:
    values: dict[str, object] = {
        "tool_id": "fixture.reference",
        "input_data": input_data or {"reference": "fixture-token://tool-input"},
        "idempotency_key": key,
        "workflow_run_id": WORKFLOW_ID,
        "task_run_id": TASK_ID,
    }
    values.update(updates)
    return ToolRequest(**values)  # type: ignore[arg-type]


def tool_grant(**updates: object) -> ToolGrant:
    values: dict[str, object] = {
        "workspace_id": WORKSPACE_ID,
        "project_id": PROJECT_ID,
        "task_run_id": TASK_ID,
        "allowed_tool_ids": frozenset({"fixture.reference"}),
        "allowed_permissions": frozenset({Permission.TOOL_RUN.value}),
    }
    values.update(updates)
    return ToolGrant(**values)  # type: ignore[arg-type]


def build_tool_gateway(
    descriptor: ToolDescriptor | None = None,
    executor: FakeToolExecutor | None = None,
) -> tuple[ToolGateway, ToolRegistry, InMemoryToolCallLedger, MemoryAudit]:
    registry = ToolRegistry()
    if descriptor is not None:
        registry.register(descriptor, executor or FakeToolExecutor())
    ledger = InMemoryToolCallLedger()
    audit = MemoryAudit()
    gateway = ToolGateway(
        registry, ledger, AuthorizationService(audit, MutableClock()), MutableClock()
    )
    return gateway, registry, ledger, audit


def test_tool_success_registry_and_public_contract() -> None:
    descriptor = tool_descriptor()
    executor = FakeToolExecutor()
    gateway, registry, ledger, audit = build_tool_gateway(descriptor, executor)
    result = asyncio.run(gateway.invoke(context(), tool_grant(), tool_request()))
    assert result.output_reference.startswith("tool-output://fixture.reference/")
    assert ledger.records[-1].status is ToolCallStatus.SUCCEEDED
    assert asyncio.run(ledger.for_workflow(WORKSPACE_ID, WORKFLOW_ID)) == tuple(ledger.records)
    assert asyncio.run(ledger.for_workflow(uuid4(), WORKFLOW_ID)) == ()
    assert audit.events[-1].action == Permission.TOOL_RUN.value
    assert tool_public.ToolDescriptor is ToolDescriptor
    assert TOOL_PROTOCOL_VERSION == "tools.v1"
    assert PLUGIN_MANIFEST_PROTOCOL_VERSION == "plugin-manifest.v1"
    assert descriptor.idempotent
    assert registry.tools == (descriptor,)
    assert registry.resolve("missing") is None
    with pytest.raises(ValueError, match="already"):
        registry.register(descriptor, executor)
    with pytest.raises(ValueError, match="tool id"):
        tool_request(tool_id="")
    with pytest.raises(ValueError, match="opaque reference"):
        ToolResult({}, "raw output")


def test_tool_schema_subset_and_fake_delay_paths() -> None:
    malformed = tool_descriptor(input_schema={"type": "object", "properties": [], "required": []})
    gateway = build_tool_gateway(malformed)[0]
    with pytest.raises(ToolGatewayError) as malformed_error:
        asyncio.run(gateway.invoke(context(), tool_grant(), tool_request()))
    assert malformed_error.value.code is ToolErrorCode.SCHEMA_INVALID

    missing = tool_descriptor()
    missing_gateway = build_tool_gateway(missing)[0]
    with pytest.raises(ToolGatewayError) as missing_error:
        asyncio.run(
            missing_gateway.invoke(
                context(), tool_grant(), tool_request(input_data={"unexpected": "fixture"})
            )
        )
    assert missing_error.value.code is ToolErrorCode.SCHEMA_INVALID

    bad_type_gateway = build_tool_gateway(tool_descriptor())[0]
    with pytest.raises(ToolGatewayError) as type_error:
        asyncio.run(
            bad_type_gateway.invoke(
                context(), tool_grant(), tool_request(input_data={"reference": 3})
            )
        )
    assert type_error.value.code is ToolErrorCode.SCHEMA_INVALID

    metadata_only = tool_descriptor(
        input_schema={
            "type": "object",
            "properties": {"reference": "metadata-only"},
            "required": ["reference"],
            "additionalProperties": False,
        },
        timeout_seconds=0.2,
    )
    delayed = FakeToolExecutor({"fixture-delay": FakeToolBehavior(FakeToolScenario.SUCCESS, 0.001)})
    delay_gateway = build_tool_gateway(metadata_only, delayed)[0]
    with pytest.raises(ToolGatewayError) as metadata_error:
        asyncio.run(delay_gateway.invoke(context(), tool_grant(), tool_request("fixture-delay")))
    assert metadata_error.value.code is ToolErrorCode.SCHEMA_INVALID

    valid_delay_gateway = build_tool_gateway(tool_descriptor(timeout_seconds=0.2), delayed)[0]
    assert asyncio.run(
        valid_delay_gateway.invoke(context(), tool_grant(), tool_request("fixture-delay"))
    ).output_reference


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"tool_id": ""}, "tool id"),
        ({"version": "v1"}, "major.minor.patch"),
        ({"capabilities": ()}, "capabilities"),
        ({"timeout_seconds": 0}, "timeout"),
        ({"input_schema": {"type": "string"}}, "objects"),
        ({"allowed_network_hosts": ("https://fixture",)}, "host names"),
        ({"allowed_file_roots": ("/root",)}, "relative"),
    ],
)
def test_tool_descriptor_rejects_unsafe_contracts(updates: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        tool_descriptor(**updates)


@pytest.mark.parametrize(
    ("tool_call", "grant", "expected"),
    [
        (
            tool_request(input_data={"reference": "fixture-token://tool-input", "extra": True}),
            tool_grant(),
            ToolErrorCode.SCHEMA_INVALID,
        ),
        (
            tool_request(network_hosts=("network.fixture",)),
            tool_grant(),
            ToolErrorCode.SCOPE_VIOLATION,
        ),
        (
            tool_request(file_paths=("../escape",)),
            tool_grant(allowed_file_roots=("workspace",)),
            ToolErrorCode.SCOPE_VIOLATION,
        ),
        (
            tool_request(resources=("asset:fixture",)),
            tool_grant(),
            ToolErrorCode.SCOPE_VIOLATION,
        ),
    ],
)
def test_tool_schema_and_scope_rejections_are_audited(
    tool_call: ToolRequest,
    grant: ToolGrant,
    expected: ToolErrorCode,
) -> None:
    gateway, _registry, ledger, _audit = build_tool_gateway(tool_descriptor())
    with pytest.raises(ToolGatewayError) as captured:
        asyncio.run(gateway.invoke(context(), grant, tool_call))
    assert captured.value.code is expected
    assert ledger.records[-1].error_code is expected


def test_tool_unknown_permission_timeout_failure_and_output_guards() -> None:
    unknown, _registry, ledger, _audit = build_tool_gateway()
    with pytest.raises(ToolGatewayError) as error:
        asyncio.run(unknown.invoke(context(), tool_grant(), tool_request()))
    assert error.value.code is ToolErrorCode.UNKNOWN_TOOL
    assert ledger.records[-1].status is ToolCallStatus.UNKNOWN

    denied, _registry, denied_ledger, _audit = build_tool_gateway(tool_descriptor())
    with pytest.raises(ToolGatewayError) as grant_error:
        asyncio.run(
            denied.invoke(
                context(),
                tool_grant(allowed_tool_ids=frozenset()),
                tool_request("fixture-denied"),
            )
        )
    assert grant_error.value.code is ToolErrorCode.PERMISSION_DENIED
    assert denied_ledger.records[-1].status is ToolCallStatus.DENIED

    no_permission, _registry, no_permission_ledger, audit = build_tool_gateway(tool_descriptor())
    with pytest.raises(PermissionDeniedError):
        asyncio.run(
            no_permission.invoke(
                context(permissions=frozenset({Permission.MODEL_RUN.value})),
                tool_grant(),
                tool_request("fixture-no-permission"),
            )
        )
    assert no_permission_ledger.records == []
    assert audit.events[-1].result == "denied"

    for scenario, expected in (
        (FakeToolScenario.TIMEOUT, ToolErrorCode.TIMED_OUT),
        (FakeToolScenario.FAILURE, ToolErrorCode.EXECUTION_FAILED),
        (FakeToolScenario.INVALID_OUTPUT, ToolErrorCode.INVALID_OUTPUT),
    ):
        key = f"fixture-{scenario.value}"
        fake = FakeToolExecutor({key: FakeToolBehavior(scenario)})
        gateway, _registry, ledger, _audit = build_tool_gateway(tool_descriptor(), fake)
        with pytest.raises(ToolGatewayError) as captured:
            asyncio.run(gateway.invoke(context(), tool_grant(), tool_request(key)))
        assert captured.value.code is expected
        assert ledger.records[-1].error_code is expected
    with pytest.raises(ValueError, match="negative"):
        FakeToolBehavior(delay_seconds=-1)


def test_tool_explicit_network_file_and_resource_scopes_can_only_narrow() -> None:
    descriptor = tool_descriptor(
        allowed_network_hosts=("network.fixture",),
        allowed_file_roots=("workspace",),
        allowed_resource_types=frozenset({"asset"}),
    )
    request = tool_request(
        network_hosts=("network.fixture",),
        file_paths=("workspace/fixture.txt",),
        resources=("asset:fixture",),
    )
    grant = tool_grant(
        allowed_network_hosts=frozenset({"network.fixture"}),
        allowed_file_roots=("workspace",),
        allowed_resources=frozenset({"asset:fixture"}),
    )
    gateway = build_tool_gateway(descriptor)[0]
    assert asyncio.run(gateway.invoke(context(), grant, request)).output_reference

    absolute = tool_request(file_paths=("/workspace/fixture",))
    with pytest.raises(ToolGatewayError) as captured:
        asyncio.run(gateway.invoke(context(), grant, absolute))
    assert captured.value.code is ToolErrorCode.SCOPE_VIOLATION


def test_plugin_manifest_loader_is_repository_confined_and_trust_is_external(
    tmp_path: Path,
) -> None:
    fixture_root = Path(__file__).parent / "fixtures" / "plugins"
    trusted_loader = RepositoryPluginLoader(
        fixture_root, trusted_signatures=frozenset({"fixture-signature"})
    )
    manifest = trusted_loader.load("fixture-plugin/manifest.json")
    assert manifest.trust_status is PluginTrustStatus.TRUSTED
    registry = ToolRegistry()
    registry.register_plugin(manifest)
    assert registry.plugins == (manifest,)
    with pytest.raises(ValueError, match="already"):
        registry.register_plugin(manifest)

    untrusted = RepositoryPluginLoader(fixture_root, trusted_signatures=frozenset()).load(
        "fixture-plugin/manifest.json"
    )
    assert untrusted.trust_status is PluginTrustStatus.UNTRUSTED
    with pytest.raises(ValueError, match="trusted"):
        ToolRegistry().register_plugin(untrusted)
    disabled = PluginManifest(
        "fixture-disabled",
        "1.0.0",
        ">=0.0.0",
        ("fixture",),
        frozenset(),
        None,
        PluginTrustStatus.UNSIGNED,
        False,
    )
    with pytest.raises(ValueError, match="trusted"):
        ToolRegistry().register_plugin(disabled)
    with pytest.raises(ValueError, match="plugin id"):
        PluginManifest(
            "", "1.0.0", ">=0", ("fixture",), frozenset(), None, PluginTrustStatus.UNSIGNED, False
        )
    with pytest.raises(ValueError, match="compatibility"):
        PluginManifest(
            "fixture", "1.0.0", "", (), frozenset(), None, PluginTrustStatus.UNSIGNED, False
        )

    with pytest.raises(ValueError, match="configured repository root"):
        trusted_loader.load("../manifest.json")
    with pytest.raises(ValueError, match="configured repository root"):
        trusted_loader.load("fixture-plugin/not-manifest.json")

    unsigned_dir = tmp_path / "unsigned"
    unsigned_dir.mkdir()
    unsigned = {
        "plugin_id": "fixture-unsigned",
        "version": "1.0.0",
        "core_compatibility": ">=0.0.0",
        "capabilities": ["fixture"],
        "required_permissions": [],
        "enabled": True,
    }
    (unsigned_dir / "manifest.json").write_text(json.dumps(unsigned), encoding="utf-8")
    assert (
        RepositoryPluginLoader(tmp_path, trusted_signatures=frozenset())
        .load("unsigned/manifest.json")
        .trust_status
        is PluginTrustStatus.UNSIGNED
    )
    (tmp_path / "manifest.json").write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        RepositoryPluginLoader(tmp_path, trusted_signatures=frozenset()).load("manifest.json")
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="fields"):
        RepositoryPluginLoader(tmp_path, trusted_signatures=frozenset()).load("manifest.json")
    invalid_fields = dict(unsigned, capabilities="fixture", signature=3)
    (tmp_path / "manifest.json").write_text(json.dumps(invalid_fields), encoding="utf-8")
    with pytest.raises(ValueError, match="fields"):
        RepositoryPluginLoader(tmp_path, trusted_signatures=frozenset()).load("manifest.json")


def test_gateway_workflow_executor_traces_model_tool_and_delegates() -> None:
    model_gateway, model_ledger, _clock, _audit = build_model_gateway(
        (FakeModelProvider("fake-primary"),),
        policy=model_policy(allowed_provider_ids=("fake-primary",), backup_provider_ids=()),
    )
    tool_gateway = build_tool_gateway(tool_descriptor())[0]
    base = FrameworkSmokeExecutor()
    executor = GatewayWorkflowExecutor(base, model_gateway, tool_gateway)
    smoke = StepExecution(
        WORKFLOW_ID,
        TASK_ID,
        "pass-token",
        StepKind.REFERENCE,
        1,
        "fixture-workflow-gateway",
        "fixture-token://workflow-input",
        0,
        0,
        context(),
    )
    result = asyncio.run(executor.execute(smoke))
    assert result.output_reference.startswith("tool-output://")
    assert model_ledger.records[-1].workflow_run_id == WORKFLOW_ID

    delegated = StepExecution(
        WORKFLOW_ID,
        uuid4(),
        "controlled-delay",
        StepKind.DELAY,
        1,
        "fixture-delegated",
        "fixture-token://workflow-input",
        0,
        0,
        context(),
    )
    assert asyncio.run(executor.execute(delegated)).output_reference.startswith(
        "workflow-output://"
    )
    asyncio.run(executor.compensate(delegated, "fixture-hook.v1"))
    assert base.compensations == (("fixture-delegated", "fixture-hook.v1"),)
    missing_context = StepExecution(
        WORKFLOW_ID,
        TASK_ID,
        "pass-token",
        StepKind.REFERENCE,
        1,
        "fixture-missing-context",
        "fixture-token://workflow-input",
        0,
        0,
    )
    with pytest.raises(Exception, match="security-context-missing"):
        asyncio.run(executor.execute(missing_context))
