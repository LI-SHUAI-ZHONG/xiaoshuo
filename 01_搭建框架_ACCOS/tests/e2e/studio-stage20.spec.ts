import { expect, test, type Page, type Route } from "@playwright/test";

const ACTOR_ID = "11111111-1111-4111-8111-111111111111";
const WORKSPACE_ID = "22222222-2222-4222-8222-222222222222";
const PROJECT_ID = "33333333-3333-4333-8333-333333333333";
const WORKFLOW_ID = "44444444-4444-4444-8444-444444444444";
const AGENT_RUN_ID = "55555555-5555-4555-8555-555555555555";
const EVENT_ONE_ID = "66666666-6666-4666-8666-666666666666";
const EVENT_TWO_ID = "77777777-7777-4777-8777-777777777777";
const STEP_ID = "88888888-8888-4888-8888-888888888888";
const TASK_ID = "99999999-9999-4999-8999-999999999999";
const CONSENT_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const NOW = "2026-09-17T12:00:00Z";

type Role = "owner" | "viewer";

interface FakeState {
  consentActive: boolean;
  eventRequests: number;
  workflowStatus: "running" | "succeeded";
}

function pageMetadata(total: number) {
  return { limit: 100, next_cursor: null, total };
}

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({ body: JSON.stringify(body), contentType: "application/json", status });
}

function errorBody(code: string) {
  return {
    error: {
      code,
      correlation_id: EVENT_ONE_ID,
      details: {},
      message: code,
      trace_id: EVENT_TWO_ID,
    },
  };
}

function project() {
  return {
    archived_at: null,
    created_at: NOW,
    created_by: ACTOR_ID,
    id: PROJECT_ID,
    name: "fixture-project",
    settings: { asset_retention_days: 30, revision_retention_limit: 100 },
    status: "active",
    updated_at: NOW,
    version: 1,
    workspace_id: WORKSPACE_ID,
  };
}

function workflowRun(status: FakeState["workflowStatus"]) {
  return {
    correlation_id: EVENT_ONE_ID,
    created_at: NOW,
    current_step_position: status === "succeeded" ? 1 : 0,
    definition_name: "framework_smoke",
    definition_version: 1,
    error_reference: null,
    id: WORKFLOW_ID,
    input_reference: "fixture-token://framework-smoke",
    output_reference: status === "succeeded" ? "fixture-result://framework-smoke" : null,
    project_id: PROJECT_ID,
    requested_by: ACTOR_ID,
    status,
    updated_at: NOW,
    version: status === "succeeded" ? 2 : 1,
    workspace_id: WORKSPACE_ID,
  };
}

function sseEvent(sequence: number, type: string, eventId: string) {
  return {
    correlation_id: EVENT_ONE_ID,
    event_id: eventId,
    occurred_at: NOW,
    payload: { schema: "fixture.v1" },
    project_id: PROJECT_ID,
    run_id: WORKFLOW_ID,
    schema_version: 1,
    sequence,
    type,
  };
}

async function installStage20Api(page: Page, role: Role): Promise<FakeState> {
  const state: FakeState = { consentActive: false, eventRequests: 0, workflowStatus: "running" };

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const method = request.method();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path === "/api/v1/identity/me") {
      await fulfillJson(route, {
        actor_id: ACTOR_ID,
        actor_kind: "user",
        permissions:
          role === "owner"
            ? ["workspace:read", "project:read", "project:write", "agent:run", "approval:decide"]
            : ["workspace:read", "project:read"],
        policy_version: "identity-rbac-v1",
        workspace_id: WORKSPACE_ID,
      });
      return;
    }
    if (path === "/api/v1/workspaces") {
      await fulfillJson(route, {
        items: [{ archived: false, id: WORKSPACE_ID, owner_user_id: ACTOR_ID }],
        page: pageMetadata(1),
      });
      return;
    }
    if (path === `/api/v1/workspaces/${WORKSPACE_ID}`) {
      await fulfillJson(route, { archived: false, id: WORKSPACE_ID, owner_user_id: ACTOR_ID });
      return;
    }
    if (path === `/api/v1/workspaces/${WORKSPACE_ID}/projects`) {
      await fulfillJson(route, {
        items: [project()],
        page: pageMetadata(1),
        sort: "name",
        status_filter: "active",
      });
      return;
    }
    if (path === `/api/v1/projects/${PROJECT_ID}`) {
      await fulfillJson(route, project());
      return;
    }
    if (path === "/api/v1/system/health") {
      await fulfillJson(route, {
        checks: [
          { critical: true, detail: "query_ok", name: "database", status: "healthy" },
          { critical: true, detail: "pong", name: "redis", status: "healthy" },
          { critical: true, detail: "bucket_ok", name: "object_storage", status: "healthy" },
          { critical: false, detail: "fake_ready", name: "ai_provider", status: "healthy" },
        ],
        status: "ready",
        timestamp: NOW,
        version: "0.0.0",
      });
      return;
    }
    if (path === "/api/v1/system/settings") {
      await fulfillJson(route, {
        ai_provider: "fake",
        development_identity_enabled: true,
        environment: "development",
        feature_flags: [{ enabled: false, name: "real_provider_calls" }],
        log_level: "INFO",
        object_storage_region: "fixture-region",
        object_storage_tls: false,
        runtime_boundaries: [
          {
            detail: "queue_consumer_configured_liveness_unreported",
            name: "worker",
            status: "configured",
          },
          {
            detail: "relay_configured_backlog_unreported",
            name: "outbox",
            status: "configured",
          },
        ],
      });
      return;
    }
    if (path === "/api/v1/workflows") {
      await fulfillJson(route, {
        items: [
          {
            name: "framework_smoke",
            step_keys: ["director", "fake-agent", "fake-model"],
            version: 1,
          },
        ],
      });
      return;
    }
    if (path === `/api/v1/projects/${PROJECT_ID}/workflows/framework_smoke/runs`) {
      if (role === "viewer") {
        await fulfillJson(route, errorBody("permission_denied"), 403);
        return;
      }
      state.workflowStatus = "running";
      state.eventRequests = 0;
      await fulfillJson(
        route,
        {
          accepted_at: NOW,
          events_url: `/api/v1/events?run_id=${WORKFLOW_ID}`,
          run_id: WORKFLOW_ID,
          status_url: `/api/v1/workflow-runs/${WORKFLOW_ID}`,
          task_url: `/api/v1/workflow-runs/${WORKFLOW_ID}/tasks`,
        },
        202,
      );
      return;
    }
    if (path === `/api/v1/workflow-runs/${WORKFLOW_ID}`) {
      await fulfillJson(route, workflowRun(state.workflowStatus));
      return;
    }
    if (path === `/api/v1/workflow-runs/${WORKFLOW_ID}/steps`) {
      await fulfillJson(route, {
        items: [
          {
            attempt: state.workflowStatus === "succeeded" ? 2 : 1,
            created_at: NOW,
            id: STEP_ID,
            position: 0,
            status: state.workflowStatus,
            step_key: "fake-model",
            updated_at: NOW,
            version: state.workflowStatus === "succeeded" ? 2 : 1,
            workflow_run_id: WORKFLOW_ID,
          },
        ],
      });
      return;
    }
    if (path === `/api/v1/workflow-runs/${WORKFLOW_ID}/tasks`) {
      await fulfillJson(route, {
        items: [
          {
            attempt: state.workflowStatus === "succeeded" ? 2 : 1,
            available_at: NOW,
            created_at: NOW,
            id: TASK_ID,
            status: state.workflowStatus,
            step_run_id: STEP_ID,
            updated_at: NOW,
            version: state.workflowStatus === "succeeded" ? 2 : 1,
            workflow_run_id: WORKFLOW_ID,
          },
        ],
      });
      return;
    }
    if (path === "/api/v1/events") {
      if (role === "viewer") {
        await fulfillJson(route, errorBody("permission_denied"), 403);
        return;
      }
      state.eventRequests += 1;
      const cursor = request.headers()["last-event-id"];
      if (state.eventRequests === 2 && cursor) {
        await fulfillJson(route, errorBody("event_cursor_expired"), 409);
        return;
      }
      const finalEvent = state.eventRequests >= 3;
      if (finalEvent) state.workflowStatus = "succeeded";
      const sequence = finalEvent ? 2 : 1;
      const event = sseEvent(
        sequence,
        finalEvent ? "workflows.run-succeeded" : "workflows.run-started",
        finalEvent ? EVENT_TWO_ID : EVENT_ONE_ID,
      );
      await route.fulfill({
        body: `retry: 10\nid: ${WORKFLOW_ID}:${String(sequence)}\nevent: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`,
        contentType: "text/event-stream",
        status: 200,
      });
      return;
    }
    if (path === "/api/v1/agents") {
      await fulfillJson(route, {
        items: [
          {
            agent_id: "director",
            allowed_tool_ids: ["fixture.reference"],
            budget_limit: {
              max_calls: 8,
              max_duration_seconds: 30,
              max_parallelism: 1,
              max_recursion_depth: 2,
              max_steps: 4,
              max_tokens: 2048,
            },
            capabilities: ["workflow_selection"],
            model_policy_id: "fake-policy",
            model_policy_version: "1",
            version: "1",
          },
        ],
      });
      return;
    }
    if (path === "/api/v1/models/status") {
      await fulfillJson(route, {
        protocol_version: "models.v1",
        providers: [
          {
            capabilities: ["text"],
            circuit_open_until: null,
            consecutive_failures: 0,
            in_flight: 0,
            provider_id: "fake",
            state: "available",
          },
        ],
      });
      return;
    }
    if (path === "/api/v1/tools/status") {
      await fulfillJson(route, {
        protocol_version: "tools.v1",
        tools: [
          {
            capabilities: ["fixture.reference"],
            configured: true,
            idempotent: true,
            tool_id: "fixture.reference",
            version: "1",
          },
        ],
      });
      return;
    }
    if (path === `/api/v1/projects/${PROJECT_ID}/agents/director/runs`) {
      if (role === "viewer") {
        await fulfillJson(route, errorBody("permission_denied"), 403);
        return;
      }
      await fulfillJson(
        route,
        {
          accepted_at: NOW,
          events_url: `/api/v1/events?run_id=${WORKFLOW_ID}`,
          run_id: AGENT_RUN_ID,
          status_url: `/api/v1/agent-runs/${AGENT_RUN_ID}`,
          task_url: `/api/v1/workflow-runs/${WORKFLOW_ID}/tasks`,
        },
        202,
      );
      return;
    }
    if (path === `/api/v1/agent-runs/${AGENT_RUN_ID}`) {
      await fulfillJson(route, {
        agent_id: "director",
        agent_version: "1",
        attempt: 1,
        correlation_id: EVENT_ONE_ID,
        created_at: NOW,
        error_code: null,
        id: AGENT_RUN_ID,
        model_calls: 1,
        project_id: PROJECT_ID,
        protected_operations: [],
        requested_by: ACTOR_ID,
        result_kind: "workflow_selection",
        result_reference: "fixture-result://director",
        status: "succeeded",
        tokens: 64,
        tool_calls: 1,
        updated_at: NOW,
        workflow_run_id: WORKFLOW_ID,
        workspace_id: WORKSPACE_ID,
      });
      return;
    }
    if (path === `/api/v1/projects/${PROJECT_ID}/feedback/behavior-consent`) {
      if (method === "POST") {
        if (role === "viewer") {
          await fulfillJson(route, errorBody("permission_denied"), 403);
          return;
        }
        state.consentActive = true;
        await fulfillJson(
          route,
          {
            actor_id: ACTOR_ID,
            granted_at: NOW,
            id: CONSENT_ID,
            policy_version: "behavior-consent-v1",
            project_id: PROJECT_ID,
            status: "active",
            withdrawn_at: null,
            workspace_id: WORKSPACE_ID,
          },
          201,
        );
        return;
      }
      if (method === "DELETE") {
        state.consentActive = false;
        await fulfillJson(route, {
          anonymized_event_ids: [EVENT_ONE_ID],
          consent: {
            actor_id: ACTOR_ID,
            granted_at: NOW,
            id: CONSENT_ID,
            policy_version: "behavior-consent-v1",
            project_id: PROJECT_ID,
            status: "withdrawn",
            withdrawn_at: NOW,
            workspace_id: WORKSPACE_ID,
          },
          tombstone_count: 1,
        });
        return;
      }
      await fulfillJson(route, {
        active: state.consentActive,
        consent: state.consentActive
          ? {
              actor_id: ACTOR_ID,
              granted_at: NOW,
              id: CONSENT_ID,
              policy_version: "behavior-consent-v1",
              project_id: PROJECT_ID,
              status: "active",
              withdrawn_at: null,
              workspace_id: WORKSPACE_ID,
            }
          : null,
      });
      return;
    }

    await fulfillJson(route, errorBody("resource_not_found"), 404);
  });
  return state;
}

async function connectLocalSession(page: Page) {
  await page.getByLabel("Workspace ID").fill(WORKSPACE_ID);
  await page.getByLabel("开发 Bearer Token").fill("fixture-token");
  await page.getByRole("button", { name: "连接本地身份" }).click();
}

test("owner monitors SSE recovery, Agent usage, consent, and system truth", async ({ page }) => {
  await installStage20Api(page, "owner");
  await page.goto(`/projects/${PROJECT_ID}/workflows`);
  await connectLocalSession(page);

  await expect(page.getByRole("heading", { name: "技术工作流监控" })).toBeVisible();
  await page.getByRole("button", { name: "提交 framework_smoke" }).click();
  await expect(page.getByRole("heading", { name: "framework_smoke" })).toBeVisible();
  await expect(page.getByText("succeeded", { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/事件游标已过期或流需要重置/)).toBeVisible();
  await expect(page.getByText("workflows.run-succeeded", { exact: true })).toBeVisible();
  await expect(page.getByRole("cell", { name: "2", exact: true }).first()).toBeVisible();

  await page.getByRole("link", { name: "Agents", exact: true }).click();
  await expect(page.getByText(/REGISTERED/).first()).toBeVisible();
  await page.getByRole("button", { name: "提交 Director Run" }).click();
  await expect(page.getByText("64", { exact: true })).toBeVisible();
  await expect(page.getByText("fixture-result://director", { exact: true })).toBeVisible();

  await page.getByRole("link", { name: "Quality", exact: true }).click();
  await expect(page.getByRole("heading", { name: "一致性与质量" })).toBeVisible();
  await expect(page.getByText(/不提供“自动修改全部”/)).toBeVisible();

  await page.getByRole("link", { name: "反馈", exact: true }).click();
  await expect(page.getByRole("heading", { name: "反馈、指标与受控改进" })).toBeVisible();
  await page.getByRole("button", { name: "明确同意" }).click();
  await expect(page.getByText("已同意", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "撤回行为同意" }).click();
  await expect(page.getByRole("dialog", { name: "确认撤回行为同意" })).toBeVisible();
  await page.getByRole("dialog").getByRole("button", { name: "确认" }).click();
  await expect(page.getByText(/服务端写入 1 个 tombstone/)).toBeVisible();

  await page.getByRole("link", { name: "System", exact: true }).click();
  await expect(page.getByRole("heading", { name: "运行状态与依赖诊断" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "database" })).toBeVisible();
  await expect(page.getByText("queue_consumer_configured_liveness_unreported")).toBeVisible();

  await page.getByRole("link", { name: "Settings", exact: true }).click();
  await expect(page.getByRole("heading", { name: "脱敏运行设置" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "real_provider_calls" })).toBeVisible();

  await page.setViewportSize({ height: 844, width: 390 });
  const menu = page.getByRole("button", { name: "切换导航" });
  await menu.focus();
  await page.keyboard.press("Enter");
  await expect(menu).toHaveAttribute("aria-expanded", "true");
});

test("viewer sees read-only monitors and direct writes or SSE stay denied", async ({ page }) => {
  await installStage20Api(page, "viewer");
  await page.goto(`/projects/${PROJECT_ID}/workflows`);
  await connectLocalSession(page);

  await expect(page.getByRole("button", { name: "提交 framework_smoke" })).toHaveCount(0);
  await expect(page.getByText(/没有 agent:run/)).toBeVisible();

  const statuses = await page.evaluate(
    async ({ projectId, runId, workspaceId }) => {
      const headers = {
        Authorization: "Bearer fixture-token",
        "Content-Type": "application/json",
        "Idempotency-Key": "fixture-denied",
        "X-Workspace-ID": workspaceId,
      };
      const write = await fetch(`/api/v1/projects/${projectId}/workflows/framework_smoke/runs`, {
        body: JSON.stringify({ input_reference: "fixture://denied" }),
        headers,
        method: "POST",
      });
      const stream = await fetch(`/api/v1/events?run_id=${runId}`, { headers });
      return [write.status, stream.status];
    },
    { projectId: PROJECT_ID, runId: WORKFLOW_ID, workspaceId: WORKSPACE_ID },
  );
  expect(statuses).toEqual([403, 403]);

  await page.getByRole("link", { name: "Agents", exact: true }).click();
  await expect(page.getByRole("button", { name: "提交 Director Run" })).toHaveCount(0);
  await expect(page.getByText(/Agent 写入口已隐藏/)).toBeVisible();

  await page.getByRole("link", { name: "反馈", exact: true }).click();
  await expect(page.getByRole("button", { name: "明确同意" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "撤回行为同意" })).toHaveCount(0);
});
