"""Durable content gateway: authorization, routing, budgets, streams and recovery."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import replace
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

from accos.kernel.clock import Clock
from accos.kernel.errors import (
    InvalidRequestError,
    KernelError,
    ResourceNotFoundError,
    ScopeViolationError,
)
from accos.kernel.security import SecurityContext
from accos.kernel.shared_contracts import CapabilityRequirement, CapabilityStatus, ContentRef
from accos.modules.identity.account_service import AccountService
from accos.modules.identity.public import AuthorizationRequest, Permission, ResourceScope
from accos.modules.memory.public import ContextBuilder
from accos.modules.models.budgets import BudgetLedger, Reservation, SharedQuota
from accos.modules.models.invocation import (
    TERMINAL,
    CallRecord,
    ModelInvocation,
    ModelMessage,
    ModelRuntimeError,
    ProviderOutput,
    TokenUsage,
)
from accos.modules.models.prompts import PromptRegistry
from accos.modules.models.registry import ModelPolicyV2, ProviderProfile
from accos.modules.models.runtime_ports import ContentProvider, ContentStore, ModelStore
from accos.modules.models.schema import validate_schema, validate_value
from accos.modules.projects.public import ProjectRepository, ProjectStatus


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


class ModelRuntime:
    def __init__(
        self,
        store: ModelStore,
        ledger: BudgetLedger,
        quota: SharedQuota,
        content: ContentStore,
        accounts: AccountService,
        projects: ProjectRepository,
        providers: dict[str, ContentProvider],
        prompts: PromptRegistry,
        clock: Clock,
        contexts: ContextBuilder,
        *,
        calls_enabled: bool,
        local_endpoints: tuple[str, ...],
    ) -> None:
        self.store, self.ledger, self.quota, self.content = store, ledger, quota, content
        self.accounts, self.projects, self.providers, self.prompts = (
            accounts,
            projects,
            providers,
            prompts,
        )
        self.clock, self.contexts, self.calls_enabled, self.local_endpoints = (
            clock,
            contexts,
            calls_enabled,
            local_endpoints,
        )

    async def authorize(
        self, context: SecurityContext, project: UUID, *, write: bool = False
    ) -> SecurityContext:
        context = replace(context, project_id=project)
        value = await self.projects.get(context.workspace_id, project)
        if value is None:
            raise ScopeViolationError
        await self.accounts.authorizer.authorize(
            AuthorizationRequest(
                context,
                Permission.MODEL_RUN if write else Permission.PROJECT_READ,
                ResourceScope(context.workspace_id, "project", str(project), project),
            )
        )
        if write and value.status is ProjectStatus.ARCHIVED:
            raise InvalidRequestError("Archived projects cannot run models.")
        return context

    async def configuration_access(self, context: SecurityContext, *, write: bool = False) -> None:
        if write:
            await self.accounts.human(context)
        await self.accounts.authorize(
            context,
            Permission.MEMBERSHIP_MANAGE if write else Permission.WORKSPACE_READ,
            "models",
            "configuration",
        )

    async def capability(self, context: SecurityContext) -> CapabilityStatus:
        await self.configuration_access(context)
        profiles = await self.store.profiles(context.workspace_id)
        policies = await self.store.policies(context.workspace_id)
        budget = await self.store.budget(context.workspace_id)
        missing = []
        if not self.calls_enabled:
            missing.append("REAL_PROVIDER_CALLS_DISABLED")
        if not profiles or not policies:
            missing.append("MODEL_PROFILE_AND_POLICY_REQUIRED")
        if budget.version == 0:
            missing.append("BUDGET_CONFIGURATION_REQUIRED")
        return CapabilityStatus(
            capability="models.real",
            enabled=not missing,
            implementation="implemented",
            implementation_version="27.0.0",
            configuration="missing" if missing else "configured",
            health="unknown",
            verification="untested",
            data="empty",
            requirements=tuple(
                CapabilityRequirement(
                    code="CONFIG_REQUIRED",
                    kind="configuration",
                    message=item,
                    configuration_path="/settings/models",
                )
                for item in missing
            ),
        )

    async def submit(
        self, context: SecurityContext, project: UUID, request: ModelInvocation
    ) -> CallRecord:
        context = await self.authorize(context, project, write=True)
        if len(canonical(request.model_dump(mode="json"))) > 2_000_000:
            raise InvalidRequestError("Model input exceeds the content limit.")
        if request.output_schema:
            validate_schema(request.output_schema)
        for tool in request.tools:
            validate_schema(tool.parameters)
        if request.prompt:
            prompt = await self.prompts.get(context, request.prompt.id, request.prompt.version)
            if (
                prompt.checksum != request.prompt.checksum
                or request.task_kind not in prompt.allowed_tasks
            ):
                raise InvalidRequestError("Prompt pin or task does not match its release.")
            if {t.name for t in request.tools} - set(prompt.allowed_tools):
                raise InvalidRequestError("Prompt does not allow these tools.")
            if request.output_schema != prompt.output_schema:
                raise InvalidRequestError("Output schema must match the frozen prompt release.")
        # Resolve and authorize every source before queueing. The immutable reference is
        # retained in the request and read again immediately before each external attempt.
        await self._resolve(context, project, request)
        data = canonical(request.model_dump(mode="json"))
        digest = hashlib.sha256(data).hexdigest()
        existing = await self.store.find_operation(context, project, request.operation_key, digest)
        if existing:
            return existing
        input_ref = await self.content.put_snapshot(
            context, project, data, media_type="application/json"
        )
        now = self.clock.now()
        call = CallRecord(
            id=uuid4(),
            workspace_id=context.workspace_id,
            project_id=project,
            actor_id=context.actor_id,
            status="queued",
            operation_key=request.operation_key,
            input_ref=input_ref,
            policy=request.policy,
            prompt=request.prompt,
            task_kind=request.task_kind,
            kind=request.kind,
            created_at=now,
            updated_at=now,
            workflow_run_id=request.workflow_run_id,
            task_run_id=request.task_run_id,
        )
        return await self.store.create_call(
            context,
            call,
            digest,
            await self._cache_key(context, project, request),
            context.as_task_headers(),
        )

    async def get(self, context: SecurityContext, project: UUID, call_id: UUID) -> CallRecord:
        await self.authorize(context, project)
        return await self.store.get_call(context.workspace_id, project, call_id)

    async def output(self, context: SecurityContext, call: CallRecord) -> ProviderOutput:
        await self.authorize(context, call.project_id)
        if call.output_ref is None:
            raise InvalidRequestError("No finalized model output is available.")
        return ProviderOutput.model_validate_json(
            await self.content.read_snapshot(context, call.project_id, call.output_ref)
        )

    async def invoke(
        self, context: SecurityContext, project: UUID, request: ModelInvocation
    ) -> tuple[CallRecord, ProviderOutput]:
        call = await self.submit(context, project, request)
        if call.status not in TERMINAL:
            claimed = await self.store.claim(call.id, self.clock.now(), 5400)
            if claimed:
                call = await self.execute(*claimed)
            else:
                # Another worker owns this exact operation. Never issue a second request.
                async with asyncio.timeout(5400):
                    while call.status not in TERMINAL:
                        await asyncio.sleep(0.25)
                        call = await self.get(context, project, call.id)
        if call.status != "completed":
            raise ModelRuntimeError(
                call.error_code or call.status.upper(), uncertain=call.billing_status == "unknown"
            )
        return call, await self.output(context, call)

    async def run_next(self) -> bool:
        await self.store.recover_expired(self.clock.now())
        claimed = await self.store.claim(None, self.clock.now(), 5400)
        if claimed is None:
            return False
        await self.execute(*claimed)
        return True

    async def execute(self, call: CallRecord, headers: dict[str, str]) -> CallRecord:
        started = self.clock.now()
        try:
            context = SecurityContext.from_task_headers(headers)
            context = await self.authorize(context, call.project_id, write=True)
            request = ModelInvocation.model_validate_json(
                await self.content.read_snapshot(context, call.project_id, call.input_ref)
            )
            if not self.calls_enabled:
                raise ModelRuntimeError("CONFIG_REQUIRED")
            try:
                policy = await self.store.policy(
                    context.workspace_id, request.policy.id, request.policy.version
                )
            except ResourceNotFoundError:
                raise ModelRuntimeError("CONFIG_REQUIRED") from None
            if not policy.enabled or request.task_kind not in policy.allowed_tasks:
                raise ModelRuntimeError("TASK_POLICY_DENIED")
            policy = policy.model_copy(
                update={
                    "task_token_limit": min(
                        policy.task_token_limit, request.task_token_limit or policy.task_token_limit
                    ),
                    "task_call_limit": min(
                        policy.task_call_limit, request.task_call_limit or policy.task_call_limit
                    ),
                }
            )
            fingerprint = await self._cache_key(context, call.project_id, request)
            if request.cache and not request.tools and policy.cache_ttl_seconds and request.prompt:
                await self._resolve(context, call.project_id, request)
                cached = await self.store.cached(
                    context.workspace_id,
                    call.project_id,
                    fingerprint,
                    started - timedelta(seconds=policy.cache_ttl_seconds),
                )
                if cached and cached.output_ref and cached.id != call.id:
                    await self.output(context, cached)  # Recheck object access and integrity.
                    value = call.model_copy(
                        update={
                            "status": "completed",
                            "output_ref": cached.output_ref,
                            "profile": cached.profile,
                            "cache_source_id": cached.id,
                            "billing_status": "cached",
                            "cost_micro_usd": 0,
                            "usage": TokenUsage(input_tokens=0),
                            "updated_at": self.clock.now(),
                        }
                    )
                    return await self.store.update_call(value)
            call = await self._route(context, call, request, policy)
        except asyncio.CancelledError:
            # Process shutdown cannot establish whether the external provider charged.
            await asyncio.shield(self._abandon_reservations(call))
            await asyncio.shield(self._failure(call, "WORKER_INTERRUPTED", uncertain=True))
            raise
        except ModelRuntimeError as error:
            call = await self._failure(call, error.reason, uncertain=error.uncertain)
        except KernelError:
            call = await self._failure(call, "ACCESS_OR_CONTENT_UNAVAILABLE")
        except Exception:
            # Never persist exception repr, response bodies or credentials.
            await self._abandon_reservations(call)
            call = await self._failure(call, "EXECUTION_FAILED", uncertain=True)
        return call

    async def _resolve(
        self, context: SecurityContext, project: UUID, request: ModelInvocation
    ) -> ModelInvocation:
        await self.authorize(context, project, write=True)
        if request.context_package_id:
            await self.contexts.get(context, project, request.context_package_id)
        messages = []
        for message in request.messages:
            if message.content_ref:
                if message.content_ref.byte_length > 2_000_000:
                    raise InvalidRequestError("Referenced model input exceeds the content limit.")
                if message.content_ref.media_type not in {
                    "text/plain",
                    "text/markdown",
                    "application/json",
                }:
                    raise InvalidRequestError(
                        "Only text content is supported by this invocation protocol."
                    )
                data = await self.content.read_snapshot(context, project, message.content_ref)
                try:
                    message = message.model_copy(
                        update={"text": data.decode("utf-8"), "content_ref": None}
                    )
                except UnicodeError:
                    raise InvalidRequestError("Referenced model input is not UTF-8 text.") from None
            messages.append(message)
        resolved = request.model_copy(update={"messages": tuple(messages)})
        if len(canonical(resolved.model_dump(mode="json"))) > 2_000_000:
            raise InvalidRequestError("Resolved model input exceeds the content limit.")
        return resolved

    async def _cache_key(
        self, context: SecurityContext, project: UUID, request: ModelInvocation
    ) -> str:
        settings = await self.accounts.store.settings(context.workspace_id)
        return hashlib.sha256(
            canonical(
                {
                    "workspace": str(context.workspace_id),
                    "project": str(project),
                    "actor": str(context.actor_id),
                    "permissions": sorted(context.permissions),
                    "access_policy": context.policy_version,
                    "settings_version": settings.version,
                    "request": request.model_dump(
                        mode="json",
                        exclude={"operation_key", "workflow_run_id", "task_run_id", "stream"},
                    ),
                }
            )
        ).hexdigest()

    async def _route(
        self,
        context: SecurityContext,
        call: CallRecord,
        request: ModelInvocation,
        policy: ModelPolicyV2,
    ) -> CallRecord:
        attempts = 0
        last = ModelRuntimeError("CONFIG_REQUIRED")
        for pin in policy.route:
            if request.continuation_profile and pin != request.continuation_profile:
                continue
            try:
                profile = await self.store.profile(context.workspace_id, pin.id, pin.version)
            except ResourceNotFoundError:
                continue
            for _ in range(policy.attempts_per_profile):
                if attempts >= policy.max_attempts:
                    raise last
                await self._check_cancel(call)
                resolved = await self._resolve(context, call.project_id, request)
                workspace = await self.accounts.store.settings(context.workspace_id)
                try:
                    profile.require(
                        resolved,
                        cloud_allowed=workspace.values.cloud_content_allowed,
                        local_endpoints=self.local_endpoints,
                    )
                except ModelRuntimeError as error:
                    last = error
                    break
                credential = (
                    await self.accounts.resolve_secret(context.workspace_id, profile.secret_ref)
                    if profile.secret_ref
                    else None
                )
                budget = await self.store.budget(context.workspace_id)
                if budget.version == 0:
                    raise ModelRuntimeError("BUDGET_CONFIGURATION_REQUIRED")
                # UTF-8 bytes plus explicit structural overhead is a conservative local
                # preflight bound, not a claim to reproduce a vendor's tokenizer.
                estimate = TokenUsage(
                    input_tokens=len(canonical(resolved.model_dump(mode="json")))
                    + len(resolved.messages) * 64,
                    output_tokens=0 if resolved.kind == "embed" else resolved.max_output_tokens,
                )
                if estimate.total > profile.context_window:
                    last = ModelRuntimeError("CONTEXT_WINDOW_EXCEEDED")
                    break
                lease = await self.quota.acquire(
                    context.workspace_id, profile.id, budget, profile.timeout_seconds
                )
                reservation: Reservation | None = None
                try:
                    reservation = await self.ledger.reserve(
                        call,
                        profile,
                        policy,
                        budget,
                        workspace.values.daily_token_budget,
                        request.task_run_id or request.workflow_run_id or call.id,
                        estimate,
                        self.clock.now(),
                    )
                    attempts += 1
                    call = await self.store.update_call(
                        call.model_copy(
                            update={
                                "profile": profile.pin,
                                "attempt_count": attempts,
                                "billing_status": "reserved",
                                "updated_at": self.clock.now(),
                            }
                        ),
                        event=False,
                    )
                    result = await self._provider_call(context, call, resolved, profile, credential)
                    await self.ledger.settle(
                        reservation,
                        result.usage,
                        profile.price.cost(result.usage) if result.usage else None,
                        result.provider_request_id,
                        None,
                    )
                    if (
                        result.status == "completed"
                        and not result.tool_calls
                        and request.output_schema
                    ):
                        try:
                            validate_value(json.loads(result.text), request.output_schema)
                        except (ValueError, InvalidRequestError):
                            # Charged invalid content is retained, but cannot be a success.
                            output = await self.content.put_snapshot(
                                context,
                                call.project_id,
                                canonical(result.model_dump(mode="json")),
                                media_type="application/json",
                            )
                            call = call.model_copy(update={"output_ref": output})
                            raise ModelRuntimeError("OUTPUT_SCHEMA_INVALID") from None
                    await self._check_cancel(call)
                    output = await self.content.put_snapshot(
                        context,
                        call.project_id,
                        canonical(result.model_dump(mode="json")),
                        media_type="application/json",
                    )
                    call = call.model_copy(
                        update={
                            "status": result.status,
                            "output_ref": output,
                            "provider_request_id": result.provider_request_id,
                            "error_code": None
                            if result.status == "completed"
                            else result.status.upper(),
                            "updated_at": self.clock.now(),
                        }
                    )
                    return await self._finish(call)
                except asyncio.CancelledError:
                    if reservation:
                        await asyncio.shield(
                            self.ledger.settle(reservation, None, None, None, "WORKER_INTERRUPTED")
                        )
                    raise
                except ModelRuntimeError as error:
                    if reservation:
                        current = await self.store.get_call(
                            call.workspace_id, call.project_id, call.id
                        )
                        await self.ledger.settle(
                            reservation,
                            None,
                            None,
                            current.provider_request_id,
                            error.reason,
                            released=not error.uncertain,
                        )
                    if error.uncertain or not error.retryable:
                        return await self._failure(call, error.reason, uncertain=error.uncertain)
                    last = error
                except Exception:
                    if reservation:
                        await self.ledger.settle(
                            reservation, None, None, None, "RESULT_PERSISTENCE_FAILED"
                        )
                    return await self._failure(call, "RESULT_PERSISTENCE_FAILED", uncertain=True)
                finally:
                    try:
                        await lease.release()
                    except Exception:
                        pass  # A quota lease expires; settlement must never be overwritten.
                await asyncio.sleep(policy.retry_delay_seconds)
        raise last

    async def _provider_call(
        self,
        context: SecurityContext,
        call: CallRecord,
        request: ModelInvocation,
        profile: ProviderProfile,
        credential: str | None,
    ) -> ProviderOutput:
        provider = self.providers[profile.protocol]

        async def run() -> ProviderOutput:
            nonlocal call
            async with asyncio.timeout(profile.timeout_seconds):
                if request.kind == "embed":
                    return await provider.embed(request, profile, credential)
                if not request.stream:
                    return await provider.invoke(request, profile, credential)
                partial, checkpoint, final = "", 0, None
                async for chunk in provider.stream(request, profile, credential):
                    if chunk.provider_request_id:
                        call = await self.store.update_call(
                            call.model_copy(
                                update={"provider_request_id": chunk.provider_request_id}
                            ),
                            event=False,
                        )
                    partial += chunk.text
                    if len(partial.encode("utf-8")) > profile.max_response_bytes:
                        raise ModelRuntimeError("RESPONSE_TOO_LARGE", uncertain=True)
                    # Store cumulative checkpoints, with monotonically increasing event
                    # sequence. A reconnect replaces the draft instead of appending twice.
                    if chunk.text and (len(partial) - checkpoint >= 512 or checkpoint == 0):
                        ref = await self.content.put_snapshot(
                            context,
                            call.project_id,
                            partial.encode("utf-8"),
                            media_type="text/plain",
                        )
                        await self.store.update_call(
                            call.model_copy(
                                update={"partial_ref": ref, "updated_at": self.clock.now()}
                            )
                        )
                        checkpoint = len(partial)
                    if chunk.result:
                        if final is not None:
                            raise ModelRuntimeError("DUPLICATE_TERMINAL_EVENT", uncertain=True)
                        final = chunk.result
                if len(partial) > checkpoint:
                    ref = await self.content.put_snapshot(
                        context, call.project_id, partial.encode("utf-8"), media_type="text/plain"
                    )
                    await self.store.update_call(
                        call.model_copy(update={"partial_ref": ref, "updated_at": self.clock.now()})
                    )
                if final is None:
                    raise ModelRuntimeError("STREAM_TRUNCATED", uncertain=True)
                return final

        task = asyncio.create_task(run())
        try:
            while not task.done():
                await asyncio.wait({task}, timeout=0.25)
                await self._check_cancel(call)
            return await task
        except TimeoutError:
            raise ModelRuntimeError("PROVIDER_TIMEOUT", uncertain=True) from None
        except (ValueError, KeyError, TypeError):
            raise ModelRuntimeError("INVALID_RESPONSE", uncertain=True) from None
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def _check_cancel(self, call: CallRecord) -> None:
        current = await self.store.get_call(call.workspace_id, call.project_id, call.id)
        if current.cancel_requested:
            raise ModelRuntimeError("CANCELLED", uncertain=current.billing_status == "reserved")
        if current.status in TERMINAL:
            raise ModelRuntimeError("OPERATION_TERMINAL", uncertain=True)

    async def _abandon_reservations(self, call: CallRecord) -> None:
        for item in await self.ledger.reservations(call.workspace_id, call.id):
            if item.status == "reserved":
                await self.ledger.settle(item, None, None, None, "WORKER_INTERRUPTED")

    async def _failure(
        self, call: CallRecord, reason: str, *, uncertain: bool = False
    ) -> CallRecord:
        current = await self.store.get_call(call.workspace_id, call.project_id, call.id)
        status = (
            "cancelled"
            if reason == "CANCELLED"
            else "unknown"
            if uncertain
            else "budget_denied"
            if reason == "BUDGET_EXHAUSTED"
            else "configuration_required"
            if reason
            in {
                "CONFIG_REQUIRED",
                "PRICE_REQUIRED",
                "BUDGET_CONFIGURATION_REQUIRED",
                "LOCAL_ENDPOINT_NOT_ALLOWLISTED",
                "CAPABILITY_UNSUPPORTED",
                "TASK_POLICY_DENIED",
                "CLOUD_CONTENT_DENIED",
            }
            else "failed"
        )
        # Preserve checkpoints committed inside streaming before a later exception.
        call = current.model_copy(
            update={
                "status": status,
                "error_code": reason,
                "updated_at": self.clock.now(),
                "output_ref": call.output_ref or current.output_ref,
            }
        )
        return await self._finish(call)

    async def _finish(self, call: CallRecord) -> CallRecord:
        current = await self.store.get_call(call.workspace_id, call.project_id, call.id)
        reservations = await self.ledger.reservations(call.workspace_id, call.id)
        unknown = any(r.status in {"unknown", "reserved"} for r in reservations)
        usages = [r.usage for r in reservations if r.usage]
        usage = (
            TokenUsage(
                input_tokens=sum(u.input_tokens for u in usages),
                output_tokens=sum(u.output_tokens for u in usages),
                cached_input_tokens=sum(u.cached_input_tokens for u in usages),
            )
            if usages
            else None
        )
        call = call.model_copy(
            update={
                "usage": usage,
                "partial_ref": current.partial_ref or call.partial_ref,
                "cost_micro_usd": None
                if unknown
                else sum(r.cost_micro_usd or 0 for r in reservations),
                "provider_request_id": call.provider_request_id or current.provider_request_id,
                "reservation_ids": tuple(r.id for r in reservations),
                "billing_status": "unknown"
                if unknown
                else "settled"
                if reservations
                else "not_started",
                "duration_ms": int((self.clock.now() - call.created_at).total_seconds() * 1000),
                "attempt_count": len(reservations),
            }
        )
        return await self.store.update_call(call)
