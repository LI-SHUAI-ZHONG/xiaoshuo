"""Stage-45 PostgreSQL/HTTP model acceptance; provider/object doubles are explicit."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
import test_content_stage26_sql

from accos.adapters.models.budgets import RedisModelQuota
from accos.kernel.features import FeatureFlags
from accos.kernel.settings import ModelSettings
from accos.modules.models.invocation import ModelRuntimeError, TokenUsage
from accos.modules.models.registry import BudgetSettings, ModelPolicyV2
from test_models_stage27 import invocation, profile

account_database = test_content_stage26_sql.account_database
content_api = test_content_stage26_sql.content_api


@pytest.fixture
def runtime_settings(runtime_settings):
    return replace(
        runtime_settings,
        models=ModelSettings(mode="real"),
        features=FeatureFlags(real_provider_calls_enabled=True),
    )


def configured(content_api):
    client, container, _storage, workspace, path = content_api
    project = path.split("/")[4]
    base = "/api/v1/projects/" + project
    item = profile("ollama")
    response = client.post(
        f"/api/v1/workspaces/{workspace}/model-profiles",
        headers={"If-Match": '"0"', "Idempotency-Key": str(uuid4())},
        json=item.model_dump(mode="json"),
    )
    assert response.status_code == 201
    policy = ModelPolicyV2(
        id="default",
        label="fixture",
        route=(item.pin,),
        allowed_tasks=("agent.task", "director.plan"),
    )
    assert (
        client.post(
            f"/api/v1/workspaces/{workspace}/model-policies",
            headers={"If-Match": '"0"', "Idempotency-Key": str(uuid4())},
            json=policy.model_dump(mode="json"),
        ).status_code
        == 201
    )
    assert (
        client.put(
            f"/api/v1/workspaces/{workspace}/budgets",
            headers={"If-Match": '"0"', "Idempotency-Key": str(uuid4())},
            json={"version": 0, "daily_cost_limit_micro_usd": 10000000},
        ).status_code
        == 200
    )
    return client, container.models.runtime, UUID(workspace), UUID(project), base, item, policy


def submit(client, base, **changes):
    request = invocation(**changes)
    response = client.post(
        base + "/model-calls",
        headers={"Idempotency-Key": request.operation_key},
        json=request.model_dump(mode="json"),
    )
    assert response.status_code == 202, response.text
    return response.json()["call"], request


@pytest.mark.integration
def test_t021_atomic_reservations_and_unknown_reconciliation(content_api):
    client, runtime, workspace, project, base, item, policy = configured(content_api)
    data, _request = submit(client, base)

    async def run():
        call = await runtime.store.get_call(workspace, project, UUID(data["id"]))
        settings = BudgetSettings(version=1, daily_cost_limit_micro_usd=100)

        async def reserve():
            return await runtime.ledger.reserve(
                call,
                item,
                policy,
                settings,
                1000,
                call.id,
                TokenUsage(input_tokens=10, output_tokens=10),
                runtime.clock.now(),
            )

        results = await asyncio.gather(*(reserve() for _ in range(8)), return_exceptions=True)
        accepted = [r for r in results if not isinstance(r, BaseException)]
        assert len(accepted) == 1
        assert all(
            isinstance(r, ModelRuntimeError) and r.reason == "BUDGET_EXHAUSTED"
            for r in results
            if isinstance(r, BaseException)
        )
        unknown = await runtime.ledger.settle(
            accepted[0], None, None, "provider-fixture", "TIMEOUT"
        )
        assert unknown.status == "unknown"
        with pytest.raises(ModelRuntimeError):
            await reserve()
        # The real public content API checks the evidence scope separately.
        fixed = await runtime.ledger.reconcile(
            workspace,
            unknown.id,
            TokenUsage(input_tokens=3, output_tokens=2),
            22,
            call.input_ref,
            call.actor_id,
        )
        replay = await runtime.ledger.reconcile(
            workspace,
            unknown.id,
            TokenUsage(input_tokens=3, output_tokens=2),
            22,
            call.input_ref,
            call.actor_id,
        )
        assert fixed == replay
        updated = await runtime.store.get_call(workspace, project, call.id)
        assert updated.cost_micro_usd == 22 and updated.billing_status == "settled"
        assert updated.status != "completed" and updated.output_ref is None

    asyncio.run(run())


@pytest.mark.integration
def test_t020_t023_deduplication_cancellation_lease_recovery_and_history(content_api):
    client, runtime, workspace, project, base, item, policy = configured(content_api)
    value, request = submit(client, base)
    repeated = client.post(
        base + "/model-calls",
        headers={"Idempotency-Key": request.operation_key},
        json=request.model_dump(mode="json"),
    )
    assert repeated.status_code == 202 and repeated.json()["call"]["id"] == value["id"]
    modified = request.model_dump(mode="json")
    modified["messages"][0]["text"] = "different request"
    assert (
        client.post(
            base + "/model-calls", headers={"Idempotency-Key": request.operation_key}, json=modified
        ).status_code
        == 409
    )
    url = base + "/model-calls/" + value["id"]
    cancelled = client.post(url + "/cancel", headers={"Idempotency-Key": str(uuid4())})
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    assert "event: model_call" in client.get(url + "/events").text
    second, _ = submit(client, base)

    async def recover():
        now = runtime.clock.now()
        claimed = await runtime.store.claim(UUID(second["id"]), now, 1)
        assert claimed is not None
        call, _headers = claimed
        assert await runtime.store.claim(call.id, now, 1) is None
        reservation = await runtime.ledger.reserve(
            call,
            item,
            policy,
            BudgetSettings(version=1, daily_cost_limit_micro_usd=100000),
            100000,
            call.id,
            TokenUsage(input_tokens=10),
            now,
        )
        await runtime.store.recover_expired(now + timedelta(seconds=2))
        recovered = await runtime.store.get_call(workspace, project, call.id)
        assert recovered.status == "unknown" and recovered.output_ref is None
        attempts = await runtime.ledger.reservations(workspace, call.id)
        assert attempts[0].id == reservation.id and attempts[0].status == "unknown"
        assert await runtime.store.claim(call.id, now + timedelta(seconds=3), 1) is None

    asyncio.run(recover())
    history = client.get(base + "/model-calls", params={"limit": 1}).json()
    assert len(history["items"]) == 1 and history["next_cursor"]
    next_page = client.get(
        base + "/model-calls", params={"cursor": history["next_cursor"], "limit": 1}
    ).json()
    assert next_page["items"][0]["id"] != history["items"][0]["id"]
    assert (
        client.get(url + "/content", params={"kind": "input"}).headers["cache-control"]
        == "private, no-store"
    )
    assert client.get(url.replace(str(project), str(uuid4()))).status_code in {403, 404}


@pytest.mark.integration
def test_t019_agent_frozen_prompt_actual_candidate_and_input_history(content_api):
    client, runtime, _workspace, _project, base, _profile, _policy = configured(content_api)
    candidate = {
        "kind": "draft",
        "summary": "fixture summary",
        "content": "actual fixture candidate 中文",
        "findings": [],
        "source_refs": [],
        "missing_inputs": [],
    }
    from accos.adapters.models.http import ModelHttpTransport
    from accos.adapters.models.real_providers import OllamaProvider
    import httpx2 as httpx

    seen = []

    def response(request):
        seen.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "done": True,
                "done_reason": "stop",
                "message": {"content": json.dumps(candidate, ensure_ascii=False)},
                "prompt_eval_count": 100,
                "eval_count": 30,
            },
        )

    runtime.providers["ollama"] = OllamaProvider(ModelHttpTransport(httpx.MockTransport(response)))
    runtime.quota = SimpleNamespace(
        acquire=AsyncMock(return_value=SimpleNamespace(release=AsyncMock()))
    )
    body = {
        "operation_key": str(uuid4()),
        "agent_id": "assistant",
        "task": "Make a candidate",
        "policy": {"id": "default", "version": 1},
        "max_tokens": 100000,
    }
    result = client.post(
        base + "/agent-tasks", headers={"Idempotency-Key": body["operation_key"]}, json=body
    )
    assert result.status_code == 202
    job = result.json()
    frozen = json.loads(
        client.get(
            base + "/agent-tasks/" + job["id"] + "/content", params={"kind": "input"}
        ).json()["text"]
    )
    assert frozen["prompt"]["checksum"] and frozen["prompt"]["version"] == "1.0.0"
    assert asyncio.run(content_api[1].agents.jobs.run_next())
    completed = client.get(base + "/agent-tasks/" + job["id"]).json()
    assert completed["status"] == "completed" and completed["result_kind"] == "draft"
    saved = client.get(base + "/agent-tasks/" + job["id"] + "/content").json()
    assert json.loads(saved["text"])["content"] == candidate["content"]
    assert seen and "Make a candidate" in json.dumps(seen)
    assert client.get(base + "/agent-tasks").json()["items"][0]["id"] == job["id"]
    calls = client.get(base + "/model-calls").json()["items"]
    assert calls[0]["task_run_id"] == job["id"] and calls[0]["billing_status"] == "settled"


@pytest.mark.integration
def test_t021_redis_quota_is_shared_between_instances():
    url = os.environ.get("ACCOS_ACCEPTANCE_REDIS_URL")
    if not url:
        pytest.skip("Stage 45 requires a separately authorized isolated Redis URL")

    async def run():
        workspace = uuid4()
        settings = BudgetSettings(concurrent_calls=1, requests_per_minute=50)
        first, second = RedisModelQuota(url), RedisModelQuota(url)
        lease = await first.acquire(workspace, "first", settings, 2)
        try:
            with pytest.raises(ModelRuntimeError) as denied:
                await second.acquire(workspace, "fallback", settings, 2)
            assert denied.value.reason == "SHARED_QUOTA_EXCEEDED"
        finally:
            await lease.release()
        fresh = await second.acquire(workspace, "fallback", settings, 2)
        await fresh.release()

    asyncio.run(run())
