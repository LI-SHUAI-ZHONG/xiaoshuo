"""Model registry, routing, budgets, resilience, and invocation audit."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from accos.modules.identity.public import AuthorizationRequest, Permission, ResourceScope
from accos.modules.models.domain import (
    MetadataStatus,
    ModelCallStatus,
    ModelErrorCode,
    ModelGatewayError,
    ModelResponse,
    PromptPolicyMetadata,
    ProviderHealth,
    ProviderHealthState,
    UsageRecord,
)
from accos.modules.models.ports import ProviderError, ProviderErrorCode, UsageTotals

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from datetime import datetime

    from accos.kernel.clock import Clock
    from accos.kernel.security import SecurityContext
    from accos.modules.identity.public import AuthorizationService
    from accos.modules.models.domain import (
        ModelCapability,
        ModelPolicy,
        ModelRequest,
        ProviderResult,
    )
    from accos.modules.models.ports import ModelProvider, UsageLedger


class PromptPolicyRegistry:
    """Content-free registry for immutable prompt/policy metadata versions."""

    def __init__(self) -> None:
        self._items: dict[tuple[str, str], PromptPolicyMetadata] = {}

    def register(self, metadata: PromptPolicyMetadata) -> None:
        """Register an immutable metadata version and reject conflicting replacement."""
        key = (metadata.metadata_id, metadata.version)
        existing = self._items.get(key)
        if existing is not None and existing != metadata:
            raise ValueError("metadata version is immutable")
        self._items[key] = metadata

    def get(self, metadata_id: str, version: str) -> PromptPolicyMetadata | None:
        """Return one exact metadata version."""
        return self._items.get((metadata_id, version))

    def active(self, metadata_id: str) -> PromptPolicyMetadata | None:
        """Return the single active version, failing on invalid registry state."""
        active = [
            item
            for (item_id, _), item in self._items.items()
            if item_id == metadata_id and item.status is MetadataStatus.ACTIVE
        ]
        if len(active) > 1:
            raise ValueError("metadata id has multiple active versions")
        return active[0] if active else None


class ModelRegistry:
    """Process-local capability catalog; credentials remain in SecretProvider adapters."""

    def __init__(self) -> None:
        self._providers: dict[str, ModelProvider] = {}

    def register(self, provider: ModelProvider) -> None:
        """Register a uniquely named provider implementation."""
        if not provider.provider_id or provider.provider_id in self._providers:
            raise ValueError("provider id must be non-empty and unique")
        self._providers[provider.provider_id] = provider

    def route(self, capability: ModelCapability, policy: ModelPolicy) -> tuple[ModelProvider, ...]:
        """Return only allowlisted configured providers supporting the capability."""
        return tuple(
            provider
            for provider_id in policy.route
            if provider_id in policy.allowed_provider_ids
            and (provider := self._providers.get(provider_id)) is not None
            and capability in provider.capabilities
        )

    def capabilities(self) -> dict[str, frozenset[ModelCapability]]:
        """Expose the credential-free capability catalog."""
        return {key: value.capabilities for key, value in self._providers.items()}


@dataclass(slots=True)
class _ProviderState:
    failures: int = 0
    in_flight: int = 0
    open_until: datetime | None = None
    not_configured: bool = False


@dataclass(frozen=True, slots=True)
class _AttemptOutcome:
    status: ModelCallStatus
    error: ModelErrorCode | None
    attempted: bool
    attempt: int
    input_tokens: int
    output_tokens: int
    started_at: datetime


class ModelGateway:
    """Single authorized model boundary with shared budgets and deterministic routing."""

    def __init__(  # noqa: PLR0913 - gateway dependencies are explicit security boundaries.
        self,
        registry: ModelRegistry,
        ledger: UsageLedger,
        authorizer: AuthorizationService,
        clock: Clock,
        policy: ModelPolicy,
        *,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._registry = registry
        self._ledger = ledger
        self._authorizer = authorizer
        self._clock = clock
        self._policy = policy
        self._sleep = sleep
        self._states: dict[str, _ProviderState] = {}
        self._semaphores: dict[str, asyncio.Semaphore] = {}

    async def invoke(  # noqa: PLR0912,PLR0915 - policy flow is intentionally centralized.
        self, context: SecurityContext, request: ModelRequest
    ) -> ModelResponse:
        """Authorize, route, retry, account, and return only safe provider-neutral data."""
        await self._authorizer.authorize(
            AuthorizationRequest(
                context,
                Permission.MODEL_RUN,
                ResourceScope(
                    context.workspace_id,
                    "model_capability",
                    request.capability.value,
                    context.project_id,
                ),
            )
        )
        if request.metadata is not None and request.metadata.status is not MetadataStatus.ACTIVE:
            raise ValueError("model request metadata must be active")
        totals = await self._ledger.totals(context.workspace_id, request.task_run_id)
        if request.max_tokens > self._policy.max_tokens_per_call:
            await self._denied(context, request, ModelErrorCode.BUDGET_EXHAUSTED)
        providers = self._registry.route(request.capability, self._policy)
        if not providers:
            await self._denied(context, request, ModelErrorCode.NOT_CONFIGURED)

        overall_attempt = 0
        last_error = ModelErrorCode.PROVIDER_FAILED
        for provider in providers:
            state = self._states.setdefault(provider.provider_id, _ProviderState())
            if state.open_until is not None and self._clock.now() < state.open_until:
                await self._record(
                    context,
                    request,
                    provider.provider_id,
                    _AttemptOutcome(
                        status=ModelCallStatus.CIRCUIT_OPEN,
                        error=ModelErrorCode.CIRCUIT_OPEN,
                        attempted=False,
                        attempt=overall_attempt,
                        input_tokens=0,
                        output_tokens=0,
                        started_at=self._clock.now(),
                    ),
                )
                last_error = ModelErrorCode.CIRCUIT_OPEN
                continue
            if state.open_until is not None:
                state.open_until = None
                state.failures = 0

            for retry in range(self._policy.retries_per_provider + 1):
                if overall_attempt >= self._policy.total_attempt_limit:
                    await self._denied(context, request, ModelErrorCode.BUDGET_EXHAUSTED)
                try:
                    self._ensure_budget(totals, request.max_tokens)
                except ModelGatewayError:
                    await self._denied(context, request, ModelErrorCode.BUDGET_EXHAUSTED)
                overall_attempt += 1
                started_at = self._clock.now()
                usage = (0, 0)
                try:
                    result = await self._call(provider, request, state)
                    usage = (result.input_tokens, result.output_tokens)
                    if result.total_tokens > request.max_tokens:
                        raise ModelGatewayError(ModelErrorCode.INVALID_RESPONSE)
                except TimeoutError:
                    status, last_error = ModelCallStatus.TIMED_OUT, ModelErrorCode.TIMED_OUT
                    usage = (0, 0)
                except ProviderError as error:
                    status, last_error = self._provider_failure(error.code)
                    state.not_configured = error.code is ProviderErrorCode.NOT_CONFIGURED
                except Exception:  # noqa: BLE001 - provider details cannot cross the gateway.
                    status, last_error = ModelCallStatus.FAILED, ModelErrorCode.INVALID_RESPONSE
                else:
                    state.failures = 0
                    state.not_configured = False
                    call_id = await self._record(
                        context,
                        request,
                        provider.provider_id,
                        _AttemptOutcome(
                            status=ModelCallStatus.SUCCEEDED,
                            error=None,
                            attempted=True,
                            attempt=overall_attempt,
                            input_tokens=result.input_tokens,
                            output_tokens=result.output_tokens,
                            started_at=started_at,
                        ),
                    )
                    return ModelResponse(
                        call_id,
                        provider.provider_id,
                        result.output_reference,
                        result.input_tokens,
                        result.output_tokens,
                        overall_attempt,
                    )

                await self._record(
                    context,
                    request,
                    provider.provider_id,
                    _AttemptOutcome(
                        status=status,
                        error=last_error,
                        attempted=True,
                        attempt=overall_attempt,
                        input_tokens=usage[0],
                        output_tokens=usage[1],
                        started_at=started_at,
                    ),
                )
                totals = self._increment_calls(totals)
                state.failures += 1
                if state.failures >= self._policy.circuit_failure_threshold:
                    state.open_until = self._clock.now() + timedelta(
                        seconds=self._policy.circuit_cooldown_seconds
                    )
                    break
                if retry < self._policy.retries_per_provider:
                    await self._sleep(self._policy.retry_backoff_seconds * (2**retry))
        raise ModelGatewayError(last_error)

    def health(self) -> tuple[ProviderHealth, ...]:
        """Return provider circuit snapshots without secrets or raw errors."""
        result: list[ProviderHealth] = []
        for provider_id in self._registry.capabilities():
            state = self._states.get(provider_id, _ProviderState())
            if state.open_until is not None and self._clock.now() < state.open_until:
                health_state = ProviderHealthState.OPEN
            elif state.not_configured:
                health_state = ProviderHealthState.NOT_CONFIGURED
            elif state.failures:
                health_state = ProviderHealthState.DEGRADED
            else:
                health_state = ProviderHealthState.AVAILABLE
            result.append(
                ProviderHealth(
                    provider_id,
                    health_state,
                    state.failures,
                    state.in_flight,
                    state.open_until,
                )
            )
        return tuple(result)

    async def _call(
        self, provider: ModelProvider, request: ModelRequest, state: _ProviderState
    ) -> ProviderResult:
        semaphore = self._semaphores.setdefault(
            provider.provider_id, asyncio.Semaphore(self._policy.concurrency_limit)
        )
        async with asyncio.timeout(self._policy.timeout_seconds):
            async with semaphore:
                state.in_flight += 1
                try:
                    return await provider.invoke(request)
                finally:
                    state.in_flight -= 1

    def _ensure_budget(self, totals: UsageTotals, requested_tokens: int) -> None:
        if (
            totals.workspace_calls >= self._policy.workspace_call_limit
            or totals.task_calls >= self._policy.task_call_limit
            or totals.workspace_tokens + requested_tokens > self._policy.workspace_token_budget
            or totals.task_tokens + requested_tokens > self._policy.task_token_budget
        ):
            raise ModelGatewayError(ModelErrorCode.BUDGET_EXHAUSTED)

    @staticmethod
    def _increment_calls(totals: UsageTotals) -> UsageTotals:
        return UsageTotals(
            totals.workspace_tokens,
            totals.workspace_calls + 1,
            totals.task_tokens,
            totals.task_calls + 1,
        )

    @staticmethod
    def _provider_failure(code: ProviderErrorCode) -> tuple[ModelCallStatus, ModelErrorCode]:
        if code is ProviderErrorCode.NOT_CONFIGURED:
            return ModelCallStatus.NOT_CONFIGURED, ModelErrorCode.NOT_CONFIGURED
        if code is ProviderErrorCode.RATE_LIMITED:
            return ModelCallStatus.RATE_LIMITED, ModelErrorCode.RATE_LIMITED
        return ModelCallStatus.FAILED, ModelErrorCode.PROVIDER_FAILED

    async def _denied(
        self,
        context: SecurityContext,
        request: ModelRequest,
        error: ModelErrorCode,
    ) -> None:
        status = (
            ModelCallStatus.NOT_CONFIGURED
            if error is ModelErrorCode.NOT_CONFIGURED
            else ModelCallStatus.BUDGET_DENIED
        )
        now = self._clock.now()
        await self._record(
            context,
            request,
            None,
            _AttemptOutcome(
                status=status,
                error=error,
                attempted=False,
                attempt=0,
                input_tokens=0,
                output_tokens=0,
                started_at=now,
            ),
        )
        raise ModelGatewayError(error)

    async def _record(
        self,
        context: SecurityContext,
        request: ModelRequest,
        provider_id: str | None,
        outcome: _AttemptOutcome,
    ) -> UUID:
        record_id = uuid4()
        await self._ledger.append(
            UsageRecord(
                record_id,
                context.workspace_id,
                context.project_id,
                request.workflow_run_id,
                request.task_run_id,
                context.actor_id,
                UUID(context.correlation.request_id),
                request.idempotency_key,
                request.capability,
                provider_id,
                outcome.status,
                outcome.error,
                outcome.attempted,
                outcome.attempt,
                outcome.input_tokens,
                outcome.output_tokens,
                outcome.started_at,
                self._clock.now(),
            )
        )
        return record_id
