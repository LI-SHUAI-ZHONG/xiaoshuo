"use client";

import type { components } from "@accos/api-client";
import { useMemo } from "react";
import { unwrapApiResult } from "../../lib/api/queries";
import { useApiClient } from "../../providers/api-provider";

export type Profile = components["schemas"]["ProviderProfile-Output"];
export type ProfileInput = components["schemas"]["ProviderProfile-Input"];
export type Policy = components["schemas"]["ModelPolicyV2"];
export type Prompt = components["schemas"]["PromptVersion"];
export type Call = components["schemas"]["CallRecord"];
export type Job = components["schemas"]["AgentJob"];
export type Budget = components["schemas"]["BudgetSettings"];
export type Invocation = components["schemas"]["ModelInvocation"];
export type AgentTask = components["schemas"]["AgentTaskInput"];
export type ContentRef = components["schemas"]["ContentRef"];

export const terminalCall = (status: string) => !["queued", "running"].includes(status);
export const pinKey = (value: { id: string; version: string | number }) =>
  value.id + "@" + value.version;
export function money(value: number | null | undefined) {
  return value == null ? "待对账" : "$" + (value / 1_000_000).toFixed(6);
}

async function allPages<T>(
  read: (cursor?: string) => Promise<{ items: T[]; next_cursor?: string | null }>,
): Promise<T[]> {
  const items: T[] = [];
  const seen = new Set<string>();
  let cursor: string | undefined;
  do {
    const page = await read(cursor);
    items.push(...page.items);
    cursor = page.next_cursor ?? undefined;
    if (cursor && seen.has(cursor)) throw new Error("配置分页游标重复，请刷新后重试。");
    if (cursor) seen.add(cursor);
  } while (cursor);
  return items;
}

export function useModelApi(workspace: string, project = "") {
  const client = useApiClient();
  return useMemo(() => {
    const header = { "X-Workspace-ID": workspace };
    const params = { header, path: { workspace_id: workspace } };
    const projectParams = { header, path: { project_id: project } };
    const write = (version?: string | number, key = crypto.randomUUID()) => ({
      ...header,
      "Idempotency-Key": key,
      ...(version === undefined ? {} : { "If-Match": '"' + version + '"' }),
    });
    return {
      profiles: () =>
        allPages<Profile>(async (cursor) =>
          unwrapApiResult(
            await client.GET("/api/v1/workspaces/{workspace_id}/model-profiles", {
              params: { ...params, query: { limit: 100, ...(cursor ? { cursor } : {}) } },
            }),
          ),
        ),
      policies: () =>
        allPages<Policy>(async (cursor) =>
          unwrapApiResult(
            await client.GET("/api/v1/workspaces/{workspace_id}/model-policies", {
              params: { ...params, query: { limit: 100, ...(cursor ? { cursor } : {}) } },
            }),
          ),
        ),
      prompts: () =>
        allPages<Prompt>(async (cursor) =>
          unwrapApiResult(
            await client.GET("/api/v1/workspaces/{workspace_id}/prompt-templates", {
              params: { ...params, query: { limit: 100, ...(cursor ? { cursor } : {}) } },
            }),
          ),
        ),
      budget: async () =>
        unwrapApiResult(await client.GET("/api/v1/workspaces/{workspace_id}/budgets", { params })),
      capabilities: async () =>
        unwrapApiResult(await client.GET("/api/v1/capabilities", { params: { header } })),
      credentials: async () =>
        unwrapApiResult(await client.GET("/api/v1/settings/credentials", { params: { header } })),
      saveProfile: async (body: ProfileInput, expected: number) =>
        unwrapApiResult(
          await client.POST("/api/v1/workspaces/{workspace_id}/model-profiles", {
            body,
            params: { ...params, header: write(expected) },
          }),
        ),
      savePolicy: async (body: Policy, expected: number) =>
        unwrapApiResult(
          await client.POST("/api/v1/workspaces/{workspace_id}/model-policies", {
            body,
            params: { ...params, header: write(expected) },
          }),
        ),
      saveBudget: async (body: Budget) =>
        unwrapApiResult(
          await client.PUT("/api/v1/workspaces/{workspace_id}/budgets", {
            body,
            params: { ...params, header: write(body.version ?? 0) },
          }),
        ),
      publishPrompt: async (body: Prompt, expected: string) =>
        unwrapApiResult(
          await client.POST("/api/v1/workspaces/{workspace_id}/prompt-templates", {
            body,
            params: { ...params, header: write(expected) },
          }),
        ),
      preview: async (prompt: Prompt, task_kind: string, variables: Record<string, unknown>) =>
        unwrapApiResult(
          await client.POST("/api/v1/workspaces/{workspace_id}/prompt-preview", {
            body: { prompt, task_kind, variables },
            params,
          }),
        ),
      calls: async (cursor?: string) =>
        unwrapApiResult(
          await client.GET("/api/v1/projects/{project_id}/model-calls", {
            params: { ...projectParams, query: { limit: 20, ...(cursor ? { cursor } : {}) } },
          }),
        ),
      call: async (id: string) =>
        unwrapApiResult(
          await client.GET("/api/v1/projects/{project_id}/model-calls/{call_id}", {
            params: { ...projectParams, path: { ...projectParams.path, call_id: id } },
          }),
        ),
      submit: async (body: Invocation) =>
        unwrapApiResult(
          await client.POST("/api/v1/projects/{project_id}/model-calls", {
            body,
            params: { ...projectParams, header: write(undefined, body.operation_key) },
          }),
        ),
      cancel: async (id: string) =>
        unwrapApiResult(
          await client.POST("/api/v1/projects/{project_id}/model-calls/{call_id}/cancel", {
            params: {
              ...projectParams,
              path: { ...projectParams.path, call_id: id },
              header: write(),
            },
          }),
        ),
      content: async (id: string, kind: "input" | "output" | "partial") =>
        unwrapApiResult(
          await client.GET("/api/v1/projects/{project_id}/model-calls/{call_id}/content", {
            params: {
              ...projectParams,
              path: { ...projectParams.path, call_id: id },
              query: { kind },
            },
          }),
        ),
      attempts: async (id: string) =>
        unwrapApiResult(
          await client.GET("/api/v1/projects/{project_id}/model-calls/{call_id}/attempts", {
            params: { ...projectParams, path: { ...projectParams.path, call_id: id } },
          }),
        ),
      reconcile: async (
        id: string,
        reservation: string,
        body: components["schemas"]["ModelReconcileInput"],
      ) =>
        unwrapApiResult(
          await client.POST(
            "/api/v1/projects/{project_id}/model-calls/{call_id}/attempts/{reservation_id}/reconcile",
            {
              body,
              params: {
                ...projectParams,
                path: { ...projectParams.path, call_id: id, reservation_id: reservation },
                header: write(),
              },
            },
          ),
        ),
      agents: async () =>
        unwrapApiResult(await client.GET("/api/v1/agents", { params: { header } })),
      jobs: async (cursor?: string) =>
        unwrapApiResult(
          await client.GET("/api/v1/projects/{project_id}/agent-tasks", {
            params: { ...projectParams, query: { limit: 20, ...(cursor ? { cursor } : {}) } },
          }),
        ),
      job: async (id: string) =>
        unwrapApiResult(
          await client.GET("/api/v1/projects/{project_id}/agent-tasks/{job_id}", {
            params: { ...projectParams, path: { ...projectParams.path, job_id: id } },
          }),
        ),
      submitAgent: async (body: AgentTask) =>
        unwrapApiResult(
          await client.POST("/api/v1/projects/{project_id}/agent-tasks", {
            body,
            params: { ...projectParams, header: write(undefined, body.operation_key) },
          }),
        ),
      jobContent: async (id: string, kind: "input" | "output") =>
        unwrapApiResult(
          await client.GET("/api/v1/projects/{project_id}/agent-tasks/{job_id}/content", {
            params: {
              ...projectParams,
              path: { ...projectParams.path, job_id: id },
              query: { kind },
            },
          }),
        ),
      feedback: async (id: string, score: number) =>
        unwrapApiResult(
          await client.POST("/api/v1/projects/{project_id}/feedback", {
            body: {
              source: "user",
              schema_version: "model-rating-v1",
              signal_code: "model-output-rating",
              numeric_value: score,
              source_reference: "model-call://" + id,
            },
            params: projectParams,
          }),
        ),
    };
  }, [client, workspace, project]);
}
