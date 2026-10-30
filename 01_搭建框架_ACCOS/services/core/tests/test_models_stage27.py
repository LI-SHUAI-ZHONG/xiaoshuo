"""T017–T023 protocol and runtime regressions. Execute only at stage 45."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx2 as httpx
import pytest
from pydantic import ValidationError

from accos.adapters.models.http import ModelHttpTransport
from accos.adapters.models.real_providers import (
    ChatCompletionsProvider,
    OllamaProvider,
    OpenAIResponsesProvider,
    wire_name,
)
from accos.kernel.errors import ConcurrencyConflictError, InvalidRequestError, PermissionDeniedError
from accos.kernel.shared_contracts import ContentRef
from accos.modules.agents.domain import AgentRuntimeError
from accos.modules.agents.real_executor import RealAgentExecutor
from accos.modules.identity.domain import Role
from accos.modules.models.budgets import Reservation
from accos.modules.models.invocation import (
    ModelInvocation,
    ModelMessage,
    ModelRuntimeError,
    ProfilePin,
    ProviderChunk,
    ProviderOutput,
    TokenUsage,
    ToolDefinition,
)
from accos.modules.models.prompts import PromptRegistry, packaged_prompts
from accos.modules.models.registry import BudgetSettings, ModelPolicyV2, Price, ProviderProfile
from accos.modules.models.runtime import ModelRuntime
from accos.modules.models.schema import validate_schema, validate_value
from accos.modules.projects.public import ProjectStatus
from test_projects_assets import NOW, FixedClock, context


def profile(protocol="openai_responses", **updates):
    return ProviderProfile.model_validate(
        {
            "id": "fixture",
            "label": "Protocol fixture",
            "protocol": protocol,
            "endpoint": "http://127.0.0.1:11434",
            "locality": "local",
            "model": "fixture-model",
            "capabilities": ["text", "structured", "tools", "stream", "embedding"],
            "embedding_dimensions": 2,
            "context_window": 1000000,
            "max_output_tokens": 4096,
            "price": {
                "version": "fixture-price",
                "input_per_million": "2",
                "output_per_million": "8",
            },
            **updates,
        }
    )


def invocation(**updates):
    return ModelInvocation.model_validate(
        {
            "operation_key": str(uuid4()),
            "policy": {"id": "default", "version": 1},
            "messages": [{"role": "user", "text": "A bounded author task 中文"}],
            **updates,
        }
    )


def transport_response(document, status=200):
    return ModelHttpTransport(
        httpx.MockTransport(lambda _request: httpx.Response(status, json=document))
    )


@pytest.mark.parametrize("state", ["completed", "refused", "incomplete"])
def test_t017_responses_state_usage_and_truncated_tool_arguments(state):
    data = {
        "id": "resp_fixture",
        "status": "incomplete" if state == "incomplete" else "completed",
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "refusal", "refusal": "cannot"}
                    if state == "refused"
                    else {"type": "output_text", "text": "candidate"}
                ],
            }
        ],
        "usage": {
            "input_tokens": 20,
            "output_tokens": 4,
            "input_tokens_details": {"cached_tokens": 3},
        },
    }
    if state == "incomplete":
        data["output"].append(
            {"type": "function_call", "call_id": "partial", "name": "x", "arguments": '{"x":'}
        )
    result = asyncio.run(
        OpenAIResponsesProvider(transport_response(data)).invoke(invocation(), profile(), None)
    )
    assert result.status == state and result.usage == TokenUsage(
        input_tokens=20, output_tokens=4, cached_input_tokens=3
    )
    assert result.provider_request_id == "resp_fixture"
    if state != "completed":
        assert result.tool_calls == ()


def test_t017_tool_name_roundtrip_and_call_id_match():
    tool = ToolDefinition(
        name="content.read",
        description="Read a frozen source",
        parameters={
            "type": "object",
            "properties": {"reference": {"type": "string"}},
            "required": ["reference"],
            "additionalProperties": False,
        },
    )
    request = invocation(tools=[tool.model_dump()])
    wire = wire_name(tool.name)
    assert "." not in wire and len(wire) <= 64
    provider = OpenAIResponsesProvider(
        transport_response(
            {
                "id": "r",
                "status": "completed",
                "output": [
                    {
                        "type": "function_call",
                        "call_id": "call_one",
                        "name": wire,
                        "arguments": '{"reference":"content://one"}',
                    }
                ],
            }
        )
    )
    payload = provider.payload(request, profile(), stream=False)
    assert payload["tools"][0]["name"] == wire and payload["store"] is False
    result = asyncio.run(provider.invoke(request, profile(), None))
    assert (
        result.tool_calls[0].name == "content.read" and result.tool_calls[0].call_id == "call_one"
    )
    with pytest.raises(ValidationError):
        invocation(messages=[{"role": "tool", "text": "result", "call_id": "unmatched"}])
    with pytest.raises(ValidationError):
        invocation(
            messages=[{"role": "assistant", "text": "", "provider_items": [{"type": "reasoning"}]}]
        )


@pytest.mark.parametrize(
    ("status", "uncertain", "retryable"),
    [
        (429, False, True),
        (400, False, False),
        (401, False, False),
        (503, True, False),
        (408, True, False),
    ],
)
def test_t017_http_failures_do_not_echo_payload_or_retry_unknown(status, uncertain, retryable):
    async def run():
        async for _ in transport_response({"secret": "do-not-log-fixture"}, status).documents(
            profile(), "/responses", {}, "credential-fixture"
        ):
            pytest.fail("HTTP error yielded a result")

    with pytest.raises(ModelRuntimeError) as result:
        asyncio.run(run())
    assert result.value.uncertain is uncertain and result.value.retryable is retryable
    assert "do-not-log-fixture" not in str(result.value) and "credential-fixture" not in str(
        result.value
    )


def test_t018_distinct_chat_ollama_protocols_and_embedding_dimensions():
    request = invocation()
    chat = ChatCompletionsProvider(
        transport_response(
            {
                "id": "chat1",
                "choices": [{"message": {"content": "chat"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 4, "completion_tokens": 2},
            }
        )
    )
    ollama = OllamaProvider(
        transport_response(
            {
                "done": True,
                "done_reason": "stop",
                "message": {"content": "local"},
                "prompt_eval_count": 4,
                "eval_count": 2,
            }
        )
    )
    assert asyncio.run(chat.invoke(request, profile("chat_completions"), None)).text == "chat"
    assert asyncio.run(ollama.invoke(request, profile("ollama"), None)).text == "local"
    assert "options" in ollama.payload(request, profile("ollama"), stream=False)
    assert "max_completion_tokens" in chat.payload(
        request, profile("chat_completions"), stream=False
    )
    embed = invocation(kind="embed")
    for protocol, document in [
        (
            "openai_responses",
            {"data": [{"index": 0, "embedding": [0.2, 0.4]}], "usage": {"prompt_tokens": 3}},
        ),
        ("ollama", {"embeddings": [[0.2, 0.4]], "prompt_eval_count": 3}),
    ]:
        provider = (
            OllamaProvider(transport_response(document))
            if protocol == "ollama"
            else OpenAIResponsesProvider(transport_response(document))
        )
        value = asyncio.run(provider.embed(embed, profile(protocol), None))
        assert value.embeddings == ((0.2, 0.4),) and value.usage.input_tokens == 3
        with pytest.raises(ModelRuntimeError, match="Model execution"):
            asyncio.run(provider.embed(embed, profile(protocol, embedding_dimensions=3), None))


def test_t020_chat_stream_usage_terminal_marker_and_truncation():
    frames = [
        {
            "id": "s1",
            "choices": [{"index": 0, "delta": {"content": "中文"}, "finish_reason": None}],
        },
        {"id": "s1", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
        {"choices": [], "usage": {"prompt_tokens": 3, "completion_tokens": 2}},
    ]
    text = "".join("data: " + json.dumps(frame) + "\n\n" for frame in frames)

    async def collect(body):
        transport = ModelHttpTransport(
            httpx.MockTransport(
                lambda _request: httpx.Response(
                    200, content=body.encode(), headers={"Content-Type": "text/event-stream"}
                )
            )
        )
        return [
            chunk
            async for chunk in ChatCompletionsProvider(transport).stream(
                invocation(stream=True), profile("chat_completions"), None
            )
        ]

    chunks = asyncio.run(collect(text + "data: [DONE]\n\n"))
    assert "".join(chunk.text for chunk in chunks) == "中文"
    assert chunks[-1].result.usage == TokenUsage(input_tokens=3, output_tokens=2)
    with pytest.raises(ModelRuntimeError) as result:
        asyncio.run(collect(text))
    assert result.value.uncertain and result.value.reason == "STREAM_TRUNCATED"


def test_t019_prompt_variables_schema_checksum_and_dag():
    prompts = packaged_prompts()
    assert {p.id for p in prompts} == {
        "agent.task",
        "director.intent",
        "director.plan",
        "director.clarify",
        "director.route",
        "director.meeting_summary",
        "director.replan",
    }
    task = next(p for p in prompts if p.id == "agent.task")
    variables = {
        "task": "{{context}}",
        "context": "private source",
        "constraints": "",
        "available_tools": [],
        "available_workflows": [],
    }
    assert "{{context}}" in task.render(variables, "agent.task")[1].text
    with pytest.raises(InvalidRequestError):
        task.render({"task": "missing fields"}, "agent.task")
    with pytest.raises(InvalidRequestError):
        task.model_copy(update={"system_template": task.system_template + "changed"}).checked()
    with pytest.raises(InvalidRequestError):
        validate_schema({"$ref": "https://external.invalid/schema"})
    with pytest.raises(InvalidRequestError):
        validate_value(
            {"unexpected": 1}, {"type": "object", "properties": {}, "additionalProperties": False}
        )
    runtime = SimpleNamespace(
        prompts=SimpleNamespace(builtins={(p.id, p.version): p for p in prompts})
    )
    executor = RealAgentExecutor(runtime, None, None)
    plan = {
        "nodes": [
            {"id": "one", "task_kind": "agent.task", "input_refs": ["source"], "depends_on": []}
        ]
    }
    executor._validate_plan(plan, {"source"}, 2)
    plan["nodes"][0]["depends_on"] = ["one"]
    with pytest.raises(AgentRuntimeError):
        executor._validate_plan(plan, {"source"}, 2)


def test_t019_builtin_prompt_cannot_be_replaced_without_latest_cas():
    async def run():
        store = AsyncMock()
        store.prompts.return_value = ()
        store.prompt.return_value = None
        registry = PromptRegistry(store, packaged_prompts())
        source = next(p for p in registry.builtins.values() if p.id == "agent.task")
        candidate = source.model_copy(update={"version": "1.0.1", "checksum": ""})
        with pytest.raises(ConcurrencyConflictError):
            await registry.publish(context(Role.OWNER), candidate, None)
        store.publish_prompt.side_effect = lambda _context, data, _expected: data
        result = await registry.publish(context(Role.OWNER), candidate, "1.0.0")
        assert result.checksum and result.version == "1.0.1"

    asyncio.run(run())


def test_t022_price_privacy_and_parameter_limits():
    assert Price(version="unknown").cost(TokenUsage(input_tokens=2)) is None
    assert (
        Price(version="tiny", input_per_million="0.1", output_per_million="0").cost(
            TokenUsage(input_tokens=1)
        )
        == 1
    )
    local = profile(capabilities=["text"])
    with pytest.raises(ModelRuntimeError) as denied:
        local.require(
            invocation(stream=True), cloud_allowed=True, local_endpoints=(local.endpoint,)
        )
    assert denied.value.reason == "CAPABILITY_UNSUPPORTED"
    cloud = profile(
        endpoint="https://provider.invalid/v1",
        locality="cloud",
        secret_ref="credential://" + str(uuid4()),
    )
    with pytest.raises(ModelRuntimeError) as denied:
        cloud.require(invocation(privacy="local_only"), cloud_allowed=True, local_endpoints=())
    assert denied.value.reason == "CLOUD_CONTENT_DENIED"
    with pytest.raises(ValidationError):
        profile(allowed_parameters=["seed"], defaults={"seed": 1})


class ContentFixture:
    def __init__(self):
        self.values = {}

    async def put_snapshot(self, _context, _project, data, *, media_type):
        ref = ContentRef(
            asset_id=uuid4(),
            asset_version_id=uuid4(),
            sha256=hashlib.sha256(data).hexdigest(),
            media_type=media_type,
            byte_length=len(data),
        )
        self.values[ref.asset_version_id] = data
        return ref

    async def read_snapshot(self, _context, _project, ref):
        return self.values[ref.asset_version_id]


class ScriptedProvider:
    def __init__(self, *, uncertain=False, retry_once=False):
        self.count, self.uncertain, self.retry_once = 0, uncertain, retry_once

    async def invoke(self, *_args):
        self.count += 1
        if self.uncertain:
            raise ModelRuntimeError("PROVIDER_TIMEOUT", uncertain=True)
        if self.retry_once and self.count == 1:
            raise ModelRuntimeError("PROVIDER_RATE_LIMITED", retryable=True)
        return ProviderOutput(
            status="completed", text="candidate", usage=TokenUsage(input_tokens=10, output_tokens=2)
        )

    async def stream(self, *_args):
        self.count += 1
        yield ProviderChunk(provider_request_id="resp_stream")
        yield ProviderChunk(text="first")
        yield ProviderChunk(text=" second")
        if self.uncertain:
            raise ModelRuntimeError("STREAM_TRUNCATED", uncertain=True)
        yield ProviderChunk(
            result=ProviderOutput(
                status="completed",
                text="first second",
                usage=TokenUsage(input_tokens=10, output_tokens=2),
            )
        )


def runtime_fixture(provider):
    store, ledger, quota, accounts, projects, contexts = [AsyncMock() for _ in range(6)]
    content, records, reservations = ContentFixture(), {}, {}
    configuration = profile()
    policy = ModelPolicyV2(
        id="default",
        label="fixture",
        route=(configuration.pin,),
        allowed_tasks=("agent.task",),
        attempts_per_profile=2,
        retry_delay_seconds=0,
    )
    store.policy.return_value, store.profile.return_value = policy, configuration
    store.budget.return_value = BudgetSettings(version=1, daily_cost_limit_micro_usd=1000000)
    store.find_operation.return_value = None
    store.cached.return_value = None

    async def create(_context, call, *_args):
        records[call.id] = call
        return call

    async def update(call, **_kwargs):
        records[call.id] = call.model_copy(update={"sequence": records[call.id].sequence + 1})
        return records[call.id]

    async def reserve(call, provider_profile, _policy, _settings, _daily, _task, estimate, now):
        item = Reservation(
            id=uuid4(),
            call_id=call.id,
            attempt=len(reservations) + 1,
            profile_id=provider_profile.id,
            profile_version=1,
            price_version="fixture-price",
            status="reserved",
            reserved_tokens=estimate.total,
            reserved_micro_usd=100,
            created_at=now,
            updated_at=now,
        )
        reservations[item.id] = item
        return item

    async def settle(item, usage, cost, request_id, error, *, released=False):
        if reservations[item.id].status == "reserved":
            reservations[item.id] = item.model_copy(
                update={
                    "status": "released"
                    if released
                    else "settled"
                    if usage and cost is not None
                    else "unknown",
                    "usage": usage,
                    "cost_micro_usd": 0 if released else cost,
                    "provider_request_id": request_id,
                    "error_code": error,
                }
            )
        return reservations[item.id]

    store.create_call.side_effect, store.update_call.side_effect = create, update
    store.get_call.side_effect = lambda _workspace, _project, identifier: records[identifier]
    ledger.reserve.side_effect, ledger.settle.side_effect = reserve, settle
    ledger.reservations.side_effect = lambda _workspace, call_id: tuple(
        r for r in reservations.values() if r.call_id == call_id
    )
    accounts.store.settings.return_value = SimpleNamespace(
        version=1, values=SimpleNamespace(cloud_content_allowed=False, daily_token_budget=1000000)
    )
    projects.get.return_value = SimpleNamespace(status=ProjectStatus.ACTIVE)
    quota.acquire.return_value = SimpleNamespace(release=AsyncMock())
    runtime = ModelRuntime(
        store,
        ledger,
        quota,
        content,
        accounts,
        projects,
        {"openai_responses": provider},
        PromptRegistry(store, packaged_prompts()),
        FixedClock(),
        contexts,
        calls_enabled=True,
        local_endpoints=(configuration.endpoint,),
    )
    actor = replace(context(Role.OWNER), project_id=uuid4())
    return runtime, actor, records


@pytest.mark.parametrize("stream", [False, True])
def test_t020_t021_unknown_call_holds_budget_and_does_not_retry(stream):
    async def run():
        provider = ScriptedProvider(uncertain=True)
        runtime, actor, records = runtime_fixture(provider)
        call = await runtime.submit(actor, actor.project_id, invocation(stream=stream))
        call = call.model_copy(update={"status": "running"})
        records[call.id] = call
        result = await runtime.execute(call, actor.as_task_headers())
        assert (
            result.status == "unknown"
            and result.billing_status == "unknown"
            and result.cost_micro_usd is None
        )
        assert provider.count == 1
        attempts = await runtime.ledger.reservations(actor.workspace_id, call.id)
        assert attempts[0].status == "unknown" and attempts[0].reserved_micro_usd > 0
        if stream:
            assert result.partial_ref is not None and result.output_ref is None
            assert result.provider_request_id == "resp_stream"

    asyncio.run(run())


def test_t020_t021_complete_checkpoint_is_not_lost_and_retries_are_counted():
    async def run(stream):
        provider = ScriptedProvider(retry_once=not stream)
        runtime, actor, records = runtime_fixture(provider)
        call = await runtime.submit(actor, actor.project_id, invocation(stream=stream))
        call = call.model_copy(update={"status": "running"})
        records[call.id] = call
        result = await runtime.execute(call, actor.as_task_headers())
        assert (
            result.status == "completed"
            and result.output_ref is not None
            and result.billing_status == "settled"
        )
        assert result.attempt_count == (1 if stream else 2)
        if stream:
            assert (
                await runtime.content.read_snapshot(actor, actor.project_id, result.partial_ref)
                == b"first second"
            )
        else:
            attempts = await runtime.ledger.reservations(actor.workspace_id, call.id)
            assert [a.status for a in attempts] == ["released", "settled"]

    asyncio.run(run(False))
    asyncio.run(run(True))


def test_t022_t023_cache_scope_and_revocation_before_provider():
    async def run():
        provider = ScriptedProvider()
        runtime, actor, records = runtime_fixture(provider)
        request = invocation()
        own = await runtime._cache_key(actor, actor.project_id, request)
        assert own != await runtime._cache_key(
            replace(actor, actor_id=uuid4()), actor.project_id, request
        )
        assert own != await runtime._cache_key(actor, uuid4(), request)
        call = await runtime.submit(actor, actor.project_id, request)
        records[call.id] = call.model_copy(update={"status": "running"})
        runtime.accounts.authorizer.authorize.side_effect = PermissionDeniedError()
        result = await runtime.execute(records[call.id], actor.as_task_headers())
        assert result.status == "failed" and provider.count == 0

    asyncio.run(run())
