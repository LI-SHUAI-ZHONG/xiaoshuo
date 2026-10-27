import { expect, test, type Page, type Request, type Route } from "@playwright/test";

import type { components } from "../../packages/api-client/src/index.ts";

const ACTOR_ID = "11111111-1111-4111-8111-111111111111";
const WORKSPACE_ID = "22222222-2222-4222-8222-222222222222";
const PROJECT_ID = "33333333-3333-4333-8333-333333333333";
const OTHER_PROJECT_ID = "44444444-4444-4444-8444-444444444444";
const ARTIFACT_ID = "55555555-5555-4555-8555-555555555555";
const REVISION_ID = "66666666-6666-4666-8666-666666666666";
const ASSET_ID = "77777777-7777-4777-8777-777777777777";
const ASSET_VERSION_ID = "88888888-8888-4888-8888-888888888888";
const INGESTION_ID = "99999999-9999-4999-8999-999999999999";
const WORKFLOW_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const DOCUMENT_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const DOCUMENT_VERSION_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
const CHUNK_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";
const CITATION_ID = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee";
const MEMORY_ID = "ffffffff-ffff-4fff-8fff-ffffffffffff";
const NOW = "2026-09-07T00:00:00Z";

type Artifact = components["schemas"]["ArtifactResponse"];
type Asset = components["schemas"]["AssetResponse"];
type Memory = components["schemas"]["MemoryResponse"];
type Project = components["schemas"]["ProjectResponse"];
type Revision = components["schemas"]["RevisionResponse"];

interface FakeApiOptions {
  failArtifacts?: boolean;
  initialProject?: boolean;
  role?: "owner" | "viewer";
}

interface FakeApiState {
  artifacts: Artifact[];
  assets: Asset[];
  memories: Map<string, Memory>;
  projects: Project[];
  revisions: Revision[];
}

function project(name = "fixture-project"): Project {
  return {
    archived_at: null,
    created_at: NOW,
    created_by: ACTOR_ID,
    id: PROJECT_ID,
    name,
    settings: { asset_retention_days: 30, revision_retention_limit: 100 },
    status: "active",
    updated_at: NOW,
    version: 1,
    workspace_id: WORKSPACE_ID,
  };
}

function pageMetadata(total: number) {
  return { limit: 100, next_cursor: null, total };
}

function requestBody(request: Request): Record<string, unknown> {
  const raw = request.postData();
  if (raw === null) return {};
  const parsed: unknown = JSON.parse(raw);
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new Error("Expected an object request body");
  }
  return parsed as Record<string, unknown>;
}

function stringField(body: Record<string, unknown>, key: string): string {
  const value = body[key];
  if (typeof value !== "string") throw new Error(`Expected string field ${key}`);
  return value;
}

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({ body: JSON.stringify(body), contentType: "application/json", status });
}

function errorBody(code: "dependency_unavailable" | "permission_denied" | "resource_not_found") {
  return {
    error: {
      code,
      correlation_id: CITATION_ID,
      details: {},
      message: code,
      trace_id: CHUNK_ID,
    },
  };
}

function asset(filename: string, mediaType: string, sizeBytes: number): Asset {
  return {
    created_at: NOW,
    current: {
      content_hash: "0".repeat(64),
      created_at: NOW,
      created_by: ACTOR_ID,
      id: ASSET_VERSION_ID,
      media_type: mediaType,
      processing_status: "uploaded",
      scan_status: "not_configured",
      size_bytes: sizeBytes,
      version_number: 1,
    },
    current_version: 1,
    deletion_marked_at: null,
    duplicate: false,
    filename,
    id: ASSET_ID,
    owner_id: ACTOR_ID,
    project_id: PROJECT_ID,
    retention_until: null,
    source: "user_upload",
    status: "active",
    updated_at: NOW,
    version: 1,
    workspace_id: WORKSPACE_ID,
  };
}

async function installFakeApi(page: Page, options: FakeApiOptions = {}): Promise<FakeApiState> {
  const role = options.role ?? "owner";
  const state: FakeApiState = {
    artifacts: [],
    assets: [],
    memories: new Map(),
    projects: options.initialProject ? [project()] : [],
    revisions: [],
  };

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const method = request.method();
    const path = new URL(request.url()).pathname;

    if (path === "/api/v1/identity/me") {
      await fulfillJson(route, {
        actor_id: ACTOR_ID,
        actor_kind: "user",
        permissions:
          role === "owner"
            ? ["workspace:read", "workspace:write", "project:read", "project:write"]
            : ["workspace:read", "project:read"],
        policy_version: "rbac.v1",
        workspace_id: WORKSPACE_ID,
      });
      return;
    }
    if (path === "/api/v1/system/health") {
      await fulfillJson(route, { checks: [], status: "ready", timestamp: NOW, version: "0.0.0" });
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
      if (method === "POST") {
        if (role === "viewer") {
          await fulfillJson(route, errorBody("permission_denied"), 403);
          return;
        }
        const body = requestBody(request);
        const created = project(stringField(body, "name"));
        state.projects = [created];
        await fulfillJson(route, created, 201);
        return;
      }
      await fulfillJson(route, {
        items: state.projects,
        page: pageMetadata(state.projects.length),
        sort: "name",
        status_filter: "active",
      });
      return;
    }
    if (path.startsWith("/api/v1/projects/") && path.split("/").length === 5) {
      const requestedProjectId = path.split("/")[4];
      const selected = state.projects.find((item) => item.id === requestedProjectId);
      await fulfillJson(route, selected ?? errorBody("resource_not_found"), selected ? 200 : 404);
      return;
    }
    if (path === `/api/v1/projects/${PROJECT_ID}/artifacts`) {
      if (method === "POST") {
        if (role === "viewer") {
          await fulfillJson(route, errorBody("permission_denied"), 403);
          return;
        }
        const body = requestBody(request);
        const created: Artifact = {
          artifact_type: stringField(body, "artifact_type") as Artifact["artifact_type"],
          created_at: NOW,
          created_by: ACTOR_ID,
          current_revision: 0,
          id: ARTIFACT_ID,
          label: stringField(body, "label"),
          project_id: PROJECT_ID,
          updated_at: NOW,
          version: 1,
          workspace_id: WORKSPACE_ID,
        };
        state.artifacts = [created];
        await fulfillJson(route, created, 201);
        return;
      }
      if (options.failArtifacts) {
        await fulfillJson(route, errorBody("dependency_unavailable"), 503);
        return;
      }
      await fulfillJson(route, {
        items: state.artifacts,
        page: pageMetadata(state.artifacts.length),
        sort: "created_at",
      });
      return;
    }
    if (path === `/api/v1/projects/${PROJECT_ID}/artifacts/${ARTIFACT_ID}`) {
      const selected = state.artifacts[0];
      await fulfillJson(route, selected ?? errorBody("resource_not_found"), selected ? 200 : 404);
      return;
    }
    if (path === `/api/v1/projects/${PROJECT_ID}/artifacts/${ARTIFACT_ID}/revisions`) {
      if (method === "POST") {
        const body = requestBody(request);
        const created: Revision = {
          artifact_id: ARTIFACT_ID,
          content_hash: stringField(body, "content_hash"),
          content_reference: stringField(body, "content_reference"),
          created_at: NOW,
          created_by: ACTOR_ID,
          id: REVISION_ID,
          project_id: PROJECT_ID,
          revision_number: 1,
          workspace_id: WORKSPACE_ID,
        };
        state.revisions = [created];
        const current = state.artifacts[0];
        if (current) state.artifacts = [{ ...current, current_revision: 1, version: 2 }];
        await fulfillJson(route, created, 201);
        return;
      }
      await fulfillJson(route, {
        items: state.revisions,
        page: pageMetadata(state.revisions.length),
      });
      return;
    }
    if (path === `/api/v1/projects/${PROJECT_ID}/assets`) {
      if (method === "POST") {
        const body = requestBody(request);
        const content = stringField(body, "content_base64");
        const created = asset(
          stringField(body, "filename"),
          stringField(body, "media_type"),
          Buffer.from(content, "base64").byteLength,
        );
        state.assets = [created];
        await fulfillJson(route, created, 201);
        return;
      }
      await fulfillJson(route, {
        items: state.assets,
        page: pageMetadata(state.assets.length),
        sort: "created_at",
        status_filter: null,
      });
      return;
    }
    if (path === `/api/v1/projects/${PROJECT_ID}/knowledge/ingestion-runs`) {
      await fulfillJson(
        route,
        {
          accepted_at: NOW,
          events_url: `/api/v1/workflow-runs/${WORKFLOW_ID}/events`,
          ingestion_run_id: INGESTION_ID,
          status_url: `/api/v1/knowledge/ingestion-runs/${INGESTION_ID}`,
          task_url: `/api/v1/task-runs/${WORKFLOW_ID}`,
          workflow_run_id: WORKFLOW_ID,
        },
        202,
      );
      return;
    }
    if (path === `/api/v1/knowledge/ingestion-runs/${INGESTION_ID}`) {
      await fulfillJson(route, {
        attempt: 1,
        correlation_id: CITATION_ID,
        created_at: NOW,
        document_id: DOCUMENT_ID,
        document_version_id: DOCUMENT_VERSION_ID,
        error_code: null,
        failed_stage: null,
        id: INGESTION_ID,
        project_id: PROJECT_ID,
        requested_by: ACTOR_ID,
        retryable: false,
        status: "ready",
        updated_at: NOW,
        verification_policy: "not_required",
        verification_status: "unverified",
        workflow_run_id: WORKFLOW_ID,
        workspace_id: WORKSPACE_ID,
      });
      return;
    }
    if (path === `/api/v1/projects/${PROJECT_ID}/knowledge/search`) {
      const body = requestBody(request);
      await fulfillJson(route, {
        hits: [
          {
            citation: {
              asset_id: ASSET_ID,
              asset_version_id: ASSET_VERSION_ID,
              chunk_id: CHUNK_ID,
              document_id: DOCUMENT_ID,
              document_version_id: DOCUMENT_VERSION_ID,
              id: CITATION_ID,
              locator: "fixture:1",
              verification_status: "unverified",
            },
            content: "fixture-content",
            score: 1,
          },
        ],
        query: stringField(body, "query"),
      });
      return;
    }
    if (path === `/api/v1/projects/${PROJECT_ID}/memories` && method === "POST") {
      const body = requestBody(request);
      const created: Memory = {
        confidence: 0.5,
        content: stringField(body, "content"),
        created_at: NOW,
        created_by: ACTOR_ID,
        current: true,
        id: MEMORY_ID,
        importance: 0.5,
        logical_id: MEMORY_ID,
        memory_type: stringField(body, "memory_type"),
        observed_at: stringField(body, "observed_at"),
        project_id: PROJECT_ID,
        provenance: {
          kind: stringField(body, "provenance_kind"),
          reference: stringField(body, "provenance_reference"),
        },
        scope: stringField(body, "scope") as Memory["scope"],
        status: "active",
        valid_from: stringField(body, "valid_from"),
        valid_until: null,
        version: 1,
        workspace_id: WORKSPACE_ID,
      };
      state.memories.set(created.id, created);
      await fulfillJson(route, created, 201);
      return;
    }
    if (path === `/api/v1/projects/${PROJECT_ID}/memories/${MEMORY_ID}`) {
      const selected = state.memories.get(MEMORY_ID);
      await fulfillJson(route, selected ?? errorBody("resource_not_found"), selected ? 200 : 404);
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

test("direct routes fail safely when unauthenticated or unknown", async ({ page }) => {
  await page.goto(`/projects/${PROJECT_ID}`);
  await expect(page.getByRole("heading", { name: "需要登录" })).toBeVisible();

  await page.goto("/route-that-does-not-exist");
  await expect(page.getByRole("heading", { name: "页面未找到" })).toBeVisible();
});

test("owner completes the project, writing, knowledge, and memory skeleton flow", async ({
  page,
}) => {
  await installFakeApi(page);
  await page.goto("/dashboard");
  await connectLocalSession(page);

  await expect(page.getByRole("heading", { name: "创作概览" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "暂无 Project" })).toBeVisible();
  await page.getByLabel("Project 名称").fill("stage19-project");
  await page.getByRole("button", { name: "创建空项目" }).click();

  await expect(page).toHaveURL(`/projects/${PROJECT_ID}`);
  await expect(page.getByRole("heading", { name: "stage19-project" })).toBeVisible();
  await page.waitForLoadState("networkidle");
  await page.getByLabel("名称", { exact: true }).fill("fixture-document");
  await expect(page.getByLabel("名称", { exact: true })).toHaveValue("fixture-document");
  await page.getByLabel("类型").selectOption("document");
  await page.getByRole("button", { name: "创建空容器" }).click();
  await expect(page.getByText("已创建 fixture-document；内容仍为空。")).toBeVisible();
  await page.getByRole("tab", { name: "Artifacts · 1" }).click();
  await page.getByRole("link", { name: "打开 Writing" }).click();

  await page.getByLabel("受控技术输入").fill("fixture technical input");
  await page.getByRole("button", { name: "保存技术修订" }).click();
  await expect(page.getByText("修订 1 已由 API 保存。")).toBeVisible();

  await page.getByRole("link", { name: "Knowledge", exact: true }).click();
  await page.getByLabel("选择技术文件").setInputFiles({
    buffer: Buffer.from("fixture technical file"),
    mimeType: "text/plain",
    name: "fixture.txt",
  });
  await page.getByRole("button", { name: "上传技术文件" }).click();
  await expect(page.getByText("fixture.txt 已由 Asset API 保存。")).toBeVisible();
  await page.getByRole("button", { name: "开始摄取" }).click();
  await expect(page.getByText("ready", { exact: true }).first()).toBeVisible();
  await page.getByLabel("技术查询").fill("fixture-query");
  await page.getByRole("button", { name: "检索" }).click();
  await expect(page.getByText("fixture:1", { exact: true })).toBeVisible();

  await page.getByRole("link", { name: "Memory", exact: true }).click();
  await page.getByLabel("技术内容").fill("fixture-memory");
  await page.getByRole("button", { name: "创建技术记录" }).click();
  await expect(
    page.getByText("studio_input / studio-form://memory", { exact: true }),
  ).toBeVisible();

  await page.setViewportSize({ height: 844, width: 390 });
  const menu = page.getByRole("button", { name: "切换导航" });
  await menu.click();
  await expect(menu).toHaveAttribute("aria-expanded", "true");

  await page.reload();
  await expect(page.getByRole("heading", { name: "需要登录" })).toBeVisible();
  await connectLocalSession(page);
  await expect(page.getByRole("heading", { name: "stage19-project" })).toBeVisible();
  await page.getByLabel("Memory ID").fill(MEMORY_ID);
  await page.getByRole("button", { name: "读取" }).click();
  await expect(page.getByText("fixture-memory", { exact: true })).toBeVisible();
});

test("viewer stays read-only and direct writes remain denied", async ({ page }) => {
  await installFakeApi(page, { initialProject: true, role: "viewer" });
  await page.goto(`/projects/${PROJECT_ID}`);
  await connectLocalSession(page);

  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("main").getByText(/只读/)).toBeVisible();
  await expect(page.getByRole("button", { name: "创建空容器" })).toHaveCount(0);
  await expect(page.getByText("当前身份仅可查看，所有 Project 写操作已隐藏。")).toBeVisible();

  const status = await page.evaluate(
    async ({ workspaceId }) => {
      const response = await fetch(`/api/v1/workspaces/${workspaceId}/projects`, {
        body: JSON.stringify({ name: "fixture-denied" }),
        headers: {
          Authorization: "Bearer fixture-token",
          "Content-Type": "application/json",
          "Idempotency-Key": "fixture-viewer",
          "X-Workspace-ID": workspaceId,
        },
        method: "POST",
      });
      return response.status;
    },
    { workspaceId: WORKSPACE_ID },
  );
  expect(status).toBe(403);
});

test("cross-project and backend failures do not leak project content", async ({ page }) => {
  await installFakeApi(page, { failArtifacts: true, initialProject: true });
  await page.goto(`/projects/${PROJECT_ID}`);
  await connectLocalSession(page);
  await expect(page.getByRole("heading", { name: "服务降级" })).toBeVisible();

  await page.goto(`/projects/${OTHER_PROJECT_ID}`);
  await connectLocalSession(page);
  await expect(page.getByRole("heading", { name: "未找到内容" })).toBeVisible();
  await expect(page.getByRole("main").getByText("fixture-project", { exact: true })).toHaveCount(0);
});
