"""Run the one content-free Stage 23 vertical smoke against a live stack."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import httpx2 as httpx

JsonObject = dict[str, Any]
CONTEXT_TOKEN_BUDGET = 25
HTTP_NO_CONTENT = 204


class Api:
    def __init__(self, base_url: str, workspace_id: UUID, token: str) -> None:
        self._workspace_id = workspace_id
        self._token = token
        self.client = httpx.Client(base_url=base_url.rstrip("/"), timeout=10.0)

    def close(self) -> None:
        self.client.close()

    @property
    def workspace_id(self) -> UUID:
        return self._workspace_id

    def headers(
        self,
        *,
        idempotency_key: str | None = None,
        expected_version: int | None = None,
        workspace_id: UUID | None = None,
    ) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "X-Workspace-ID": str(workspace_id or self._workspace_id),
        }
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        if expected_version is not None:
            headers["If-Match"] = f'"{expected_version}"'
        return headers

    def request(  # noqa: PLR0913
        self,
        method: str,
        path: str,
        *,
        body: JsonObject | None = None,
        expected: tuple[int, ...] = (200,),
        idempotency_key: str | None = None,
        expected_version: int | None = None,
        workspace_id: UUID | None = None,
    ) -> JsonObject:
        response = self.client.request(
            method,
            path,
            headers=self.headers(
                idempotency_key=idempotency_key,
                expected_version=expected_version,
                workspace_id=workspace_id,
            ),
            json=body,
        )
        if response.status_code not in expected:
            error_code = "unknown"
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    error = payload.get("error")
                    if isinstance(error, dict):
                        error_code = str(error.get("code", "unknown"))
            except ValueError:
                pass
            raise RuntimeError(f"{method} {path} returned {response.status_code} ({error_code})")
        if response.status_code == HTTP_NO_CONTENT:
            return {}
        payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError(f"{method} {path} returned a non-object JSON payload")
        return cast("JsonObject", payload)


def _id(payload: JsonObject, key: str = "id") -> UUID:
    value = payload.get(key)
    if not isinstance(value, str):
        raise TypeError(f"response field {key} is not a string UUID")
    return UUID(value)


def _version(payload: JsonObject) -> int:
    value = payload.get("version")
    if not isinstance(value, int):
        raise TypeError("response version is not an integer")
    return value


def _wait_for(  # noqa: PLR0913
    api: Api,
    path: str,
    *,
    field: str,
    expected: frozenset[str],
    failed: frozenset[str],
    timeout_seconds: float = 45.0,
) -> JsonObject:
    deadline = time.monotonic() + timeout_seconds
    last = "missing"
    while time.monotonic() < deadline:
        payload = api.request("GET", path)
        last = str(payload.get(field, "missing"))
        if last in expected:
            return payload
        if last in failed:
            raise RuntimeError(f"{path} reached terminal failure state {last}")
        time.sleep(0.25)
    raise TimeoutError(f"{path} did not reach {sorted(expected)}; last state was {last}")


def _assert_sse_terminal(api: Api, run_id: UUID) -> None:
    found = False
    with api.client.stream(
        "GET",
        f"/api/v1/events?run_id={run_id}",
        headers=api.headers(),
        timeout=httpx.Timeout(10.0, read=12.0),
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line == "event: workflows.run-succeeded":
                found = True
                break
    if not found:
        raise RuntimeError("SSE stream did not expose the persisted terminal event")


def run_smoke(api: Api, approver: Api) -> JsonObject:  # noqa: PLR0912,PLR0915
    identity = api.request("GET", "/api/v1/identity/me")
    if _id(identity, "workspace_id") != api.workspace_id:
        raise RuntimeError("development identity resolved to an unexpected workspace")
    approver_identity = approver.request("GET", "/api/v1/identity/me")
    if _id(approver_identity, "workspace_id") != api.workspace_id:
        raise RuntimeError("development approver resolved to an unexpected workspace")
    if _id(approver_identity, "actor_id") == _id(identity, "actor_id"):
        raise RuntimeError("development requester and approver must be distinct actors")

    project_body: JsonObject = {
        "name": "fixture-project",
        "settings": {"asset_retention_days": 2, "revision_retention_limit": 5},
    }
    project = api.request(
        "POST",
        f"/api/v1/workspaces/{api.workspace_id}/projects",
        body=project_body,
        expected=(201,),
        idempotency_key="stage23-project-v1",
    )
    replay = api.request(
        "POST",
        f"/api/v1/workspaces/{api.workspace_id}/projects",
        body=project_body,
        expected=(201,),
        idempotency_key="stage23-project-v1",
    )
    project_id = _id(project)
    if _id(replay) != project_id:
        raise RuntimeError("project idempotency replay created a second project")

    empty = api.request(
        "POST",
        f"/api/v1/projects/{project_id}/knowledge/search",
        body={"query": "fixture-empty-query"},
    )
    if empty.get("hits") != []:
        raise RuntimeError("an empty knowledge index returned a hit")

    artifact = api.request(
        "POST",
        f"/api/v1/projects/{project_id}/artifacts",
        body={"artifact_type": "other", "label": "fixture-technical-draft"},
        expected=(201,),
    )
    artifact_id = _id(artifact)
    revision = api.request(
        "POST",
        f"/api/v1/projects/{project_id}/artifacts/{artifact_id}/revisions",
        body={
            "content_hash": hashlib.sha256(b"fixture technical draft").hexdigest(),
            "content_reference": "fixture-draft://technical-metadata",
        },
        expected=(201,),
        expected_version=_version(artifact),
    )

    asset_bytes = b"fixture technical retrieval source"
    asset = api.request(
        "POST",
        f"/api/v1/projects/{project_id}/assets",
        body={
            "content_base64": base64.b64encode(asset_bytes).decode("ascii"),
            "expected_sha256": hashlib.sha256(asset_bytes).hexdigest(),
            "filename": "fixture.txt",
            "media_type": "text/plain",
            "source": "user_upload",
        },
        expected=(201,),
    )
    asset_id = _id(asset)
    ingestion = api.request(
        "POST",
        f"/api/v1/projects/{project_id}/knowledge/ingestion-runs",
        body={"asset_id": str(asset_id), "verification_policy": "not_required"},
        expected=(202,),
        idempotency_key="stage23-ingestion-v1",
    )
    ingestion_id = _id(ingestion, "ingestion_run_id")
    _wait_for(
        api,
        f"/api/v1/knowledge/ingestion-runs/{ingestion_id}",
        field="status",
        expected=frozenset({"ready"}),
        failed=frozenset({"failed"}),
    )
    retrieval = api.request(
        "POST",
        f"/api/v1/projects/{project_id}/knowledge/search",
        body={"query": "fixture technical retrieval source", "top_k": 3},
    )
    hits = retrieval.get("hits")
    if not isinstance(hits, list) or not hits:
        raise RuntimeError("knowledge retrieval did not return a cited hit")
    first_hit = hits[0]
    if not isinstance(first_hit, dict) or not isinstance(first_hit.get("citation"), dict):
        raise RuntimeError("knowledge retrieval hit lacks citation metadata")

    now = datetime.now(UTC).isoformat()
    memory = api.request(
        "POST",
        f"/api/v1/projects/{project_id}/memories",
        body={
            "confidence": 0.5,
            "content": "fixture-memory",
            "importance": 0.5,
            "memory_type": "fixture",
            "observed_at": now,
            "provenance_kind": "fixture",
            "provenance_reference": "fixture-memory://source",
            "scope": "project",
            "valid_from": now,
        },
        expected=(201,),
    )
    memory_id = _id(memory)
    conflict = api.request(
        "POST",
        f"/api/v1/projects/{project_id}/memories/{memory_id}/revisions",
        body={"content": "fixture-memory-candidate"},
        expected=(201,),
    )
    if conflict.get("status") != "pending":
        raise RuntimeError("memory conflict did not remain pending for human review")
    context_package = api.request(
        "POST",
        f"/api/v1/projects/{project_id}/context-packages",
        body={
            "budget_chars": 100,
            "budget_tokens": CONTEXT_TOKEN_BUDGET,
            "memory_types": ["fixture"],
            "scopes": ["project"],
            "task_reference": "fixture-task://stage23-context",
        },
        expected=(201,),
    )
    if int(context_package.get("used_tokens", 0)) > CONTEXT_TOKEN_BUDGET:
        raise RuntimeError("context package exceeded its token budget")

    workflow = api.request(
        "POST",
        f"/api/v1/projects/{project_id}/workflows/framework_smoke/runs",
        body={"input_reference": "fixture-token://stage23"},
        expected=(202,),
        idempotency_key="stage23-workflow-v1",
    )
    workflow_replay = api.request(
        "POST",
        f"/api/v1/projects/{project_id}/workflows/framework_smoke/runs",
        body={"input_reference": "fixture-token://stage23"},
        expected=(202,),
        idempotency_key="stage23-workflow-v1",
    )
    workflow_id = _id(workflow, "run_id")
    if _id(workflow_replay, "run_id") != workflow_id:
        raise RuntimeError("workflow idempotency replay created a second run")
    completed_workflow = _wait_for(
        api,
        f"/api/v1/workflow-runs/{workflow_id}",
        field="status",
        expected=frozenset({"succeeded"}),
        failed=frozenset({"cancelled", "failed"}),
    )
    _assert_sse_terminal(api, workflow_id)
    refreshed_workflow = api.request("GET", f"/api/v1/workflow-runs/{workflow_id}")
    if refreshed_workflow.get("status") != completed_workflow.get("status"):
        raise RuntimeError("workflow terminal projection changed after refresh")

    director = api.request(
        "POST",
        f"/api/v1/projects/{project_id}/agents/director/runs",
        body={
            "goal_reference": "fixture-goal://stage23",
            "max_calls": 2,
            "max_steps": 2,
            "max_tokens": 64,
        },
        expected=(202,),
        idempotency_key="stage23-director-v1",
    )
    _wait_for(
        api,
        f"/api/v1/agent-runs/{_id(director, 'run_id')}",
        field="status",
        expected=frozenset({"succeeded"}),
        failed=frozenset({"failed", "rejected"}),
    )

    consistency = api.request(
        "POST",
        f"/api/v1/projects/{project_id}/consistency/checks",
        body={
            "canon_changes": [],
            "references": [{"evidence_reference": "fixture-evidence://source", "exists": True}],
            "required_fields": [
                {
                    "evidence_reference": "fixture-evidence://source",
                    "field_code": "fixture-field",
                    "present": True,
                }
            ],
            "versions": [
                {
                    "current_version": 1,
                    "evidence_reference": "fixture-evidence://source",
                    "expected_version": 1,
                }
            ],
            "workflow_run_id": str(workflow_id),
        },
        expected=(201,),
    )
    if consistency.get("status") != "passed":
        raise RuntimeError("structural consistency gate did not pass")
    illegal_canon = api.request(
        "POST",
        f"/api/v1/projects/{project_id}/consistency/checks",
        body={
            "canon_changes": [
                {
                    "canon_reference": "fixture-canon://protected",
                    "explicitly_authorized": False,
                    "level": "level_1",
                    "modifies_current": True,
                }
            ],
            "references": [],
            "required_fields": [],
            "versions": [],
            "workflow_run_id": str(workflow_id),
        },
        expected=(201,),
    )
    if illegal_canon.get("status") != "findings" or not illegal_canon.get("findings"):
        raise RuntimeError("unauthorized Canon change was not rejected by the structural gate")

    rubric = api.request(
        "POST",
        f"/api/v1/projects/{project_id}/quality/rubrics",
        body={
            "dimension_keys": ["structural-consistency"],
            "rubric_key": "fixture-rubric",
            "schema_version": "quality.v1",
            "version": 1,
        },
        expected=(201,),
    )
    evaluation = api.request(
        "POST",
        f"/api/v1/projects/{project_id}/quality/evaluations",
        body={
            "input_reference": "fixture-quality://stage23",
            "rubric_id": str(_id(rubric)),
            "workflow_run_id": str(workflow_id),
        },
        expected=(201,),
    )
    quality = api.request(
        "POST",
        f"/api/v1/projects/{project_id}/quality/evaluations/{_id(evaluation)}/execute",
        body={
            "consistency_status": "passed",
            "input_reference": "fixture-quality://stage23",
        },
    )
    if quality.get("status") != "passed":
        raise RuntimeError("structural quality gate did not pass")

    api.request(
        "POST",
        f"/api/v1/projects/{project_id}/metrics",
        body={
            "dimensions": [
                {"allowed_values": ["api", "worker"], "key": "component"},
                {
                    "allowed_values": ["healthy", "degraded", "unhealthy"],
                    "key": "status",
                },
            ],
            "name": "runtime.health",
            "retention_days": 30,
            "sensitivity": "internal",
            "unit": "count",
            "version": 1,
        },
        expected=(201,),
    )
    metric = api.request(
        "POST",
        f"/api/v1/projects/{project_id}/metric-points",
        body={
            "dimensions": {"component": "worker", "status": "unhealthy"},
            "name": "runtime.health",
            "source_reference": "fixture-metric://stage23",
            "value": 1.0,
        },
        expected=(201,),
    )
    diagnostics = api.request(
        "POST",
        f"/api/v1/projects/{project_id}/metric-points/{_id(metric)}/diagnostics",
        expected=(201,),
    )
    diagnostic_items = diagnostics.get("items")
    if not isinstance(diagnostic_items, list) or len(diagnostic_items) != 1:
        raise RuntimeError("technical metric did not create one deterministic diagnostic")
    diagnostic = diagnostic_items[0]
    if not isinstance(diagnostic, dict):
        raise TypeError("diagnostic response is invalid")
    diagnostic_payload = cast("JsonObject", diagnostic)
    proposal = api.request(
        "POST",
        f"/api/v1/projects/{project_id}/diagnostics/{_id(diagnostic_payload)}/improvement-proposals",
        expected=(201,),
    )
    proposal_id = _id(proposal)
    proposal = api.request(
        "POST",
        f"/api/v1/projects/{project_id}/improvement-proposals/{proposal_id}/plan",
        body={
            "action": "suggest-configuration",
            "change_reference": "fixture-change://stage23",
            "rollback_reference": "fixture-rollback://stage23",
        },
        expected_version=_version(proposal),
    )
    for operation in ("simulate", "evaluate", "request-approval"):
        proposal = api.request(
            "POST",
            f"/api/v1/projects/{project_id}/improvement-proposals/{proposal_id}/{operation}",
            expected_version=_version(proposal),
        )
    if proposal.get("state") != "awaiting_approval":
        raise RuntimeError("improvement proposal bypassed the human approval state")
    self_decision = api.request(
        "POST",
        f"/api/v1/projects/{project_id}/improvement-proposals/{proposal_id}/decision",
        body={"decision": "approve"},
        expected=(403,),
        expected_version=_version(proposal),
    )
    self_error = self_decision.get("error")
    if not isinstance(self_error, dict) or self_error.get("code") != "permission_denied":
        raise RuntimeError("proposal requester was not denied self-approval")
    pending_proposal = api.request(
        "GET",
        f"/api/v1/projects/{project_id}/improvement-proposals/{proposal_id}",
    )
    if pending_proposal.get("state") != "awaiting_approval" or _version(
        pending_proposal
    ) != _version(proposal):
        raise RuntimeError("denied self-approval changed the proposal")
    proposal = approver.request(
        "POST",
        f"/api/v1/projects/{project_id}/improvement-proposals/{proposal_id}/decision",
        body={"decision": "approve"},
        expected_version=_version(pending_proposal),
    )
    if proposal.get("state") != "approved" or proposal.get("approved_by") is None:
        raise RuntimeError("human approval was not persisted")

    isolation = api.request(
        "GET",
        f"/api/v1/projects/{project_id}",
        expected=(401, 403, 404),
        workspace_id=UUID("99999999-9999-4999-8999-999999999999"),
    )
    del isolation
    observability = api.request("GET", "/api/v1/system/observability")
    metric_names = observability.get("metric_names")
    if not isinstance(metric_names, list) or "accos_api_requests_total" not in metric_names:
        raise RuntimeError("observability registry is not connected to the API")

    return {
        "agent_run_id": str(_id(director, "run_id")),
        "asset_id": str(asset_id),
        "context_package_id": str(_id(context_package)),
        "human_approver_id": str(_id(approver_identity, "actor_id")),
        "human_approval_state": proposal.get("state"),
        "ingestion_run_id": str(ingestion_id),
        "memory_conflict_state": conflict.get("status"),
        "memory_id": str(memory_id),
        "project_id": str(project_id),
        "quality_status": quality.get("status"),
        "revision_id": str(_id(revision)),
        "self_approval_error": self_error.get("code"),
        "status": "PASS",
        "workflow_id": str(workflow_id),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--workspace-id", type=UUID, required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--approver-token", required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    arguments = parser.parse_args()
    api = Api(arguments.base_url, arguments.workspace_id, arguments.token)
    approver = Api(arguments.base_url, arguments.workspace_id, arguments.approver_token)
    try:
        evidence = run_smoke(api, approver)
    finally:
        api.close()
        approver.close()
    output = cast("Path", arguments.evidence).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sys.stdout.write(json.dumps(evidence, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
