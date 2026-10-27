"use client";

import type { components } from "@accos/api-client";
import { useMemo } from "react";
import { unwrapApiResult } from "../../lib/api/queries";
import { useApiClient } from "../../providers/api-provider";

export function useContentApi(workspace: string, project: string, artifact: string) {
  const client = useApiClient();
  return useMemo(() => {
    const params = {
      header: { "X-Workspace-ID": workspace },
      path: { project_id: project, artifact_id: artifact },
    };
    return {
      working: async (branch?: string) =>
        unwrapApiResult(
          await client.GET("/api/v1/projects/{project_id}/artifacts/{artifact_id}/working-copy", {
            params: { ...params, query: branch ? { branch_id: branch } : {} },
          }),
        ),
      save: async (branch: string, version: number, body: components["schemas"]["SaveContent"]) =>
        unwrapApiResult(
          await client.PUT("/api/v1/projects/{project_id}/artifacts/{artifact_id}/working-copy", {
            body,
            params: {
              ...params,
              header: {
                ...params.header,
                "If-Match": `"${version}"`,
                "Idempotency-Key": body.client_change_id,
              },
              query: { branch_id: branch },
            },
          }),
        ),
      history: async (cursor?: string) =>
        unwrapApiResult(
          await client.GET(
            "/api/v1/projects/{project_id}/artifacts/{artifact_id}/revision-history",
            { params: { ...params, query: { limit: 20, ...(cursor ? { cursor } : {}) } } },
          ),
        ),
      branches: async (cursor?: string) =>
        unwrapApiResult(
          await client.GET("/api/v1/projects/{project_id}/artifacts/{artifact_id}/branches", {
            params: { ...params, query: { limit: 100, ...(cursor ? { cursor } : {}) } },
          }),
        ),
      createBranch: async (name: string, base: string | null, key: string) =>
        unwrapApiResult(
          await client.POST("/api/v1/projects/{project_id}/artifacts/{artifact_id}/branches", {
            body: { name, base_revision_id: base },
            params: { ...params, header: { ...params.header, "Idempotency-Key": key } },
          }),
        ),
      archiveBranch: async (branch: string, version: number, archived: boolean) =>
        unwrapApiResult(
          await client.PUT(
            "/api/v1/projects/{project_id}/artifacts/{artifact_id}/branches/{branch_id}/archive",
            {
              params: {
                ...params,
                path: { ...params.path, branch_id: branch },
                query: { archived },
                header: { ...params.header, "If-Match": `"${version}"` },
              },
            },
          ),
        ),
      content: async (revision: string) =>
        unwrapApiResult(
          await client.GET("/api/v1/projects/{project_id}/artifacts/{artifact_id}/content", {
            params: { ...params, query: { revision_id: revision } },
          }),
        ),
      restore: async (
        revision: string,
        version: number,
        body: components["schemas"]["RestoreInput"],
      ) =>
        unwrapApiResult(
          await client.POST(
            "/api/v1/projects/{project_id}/artifacts/{artifact_id}/revisions/{revision_id}/restore",
            {
              body,
              params: {
                ...params,
                path: { ...params.path, revision_id: revision },
                header: {
                  ...params.header,
                  "If-Match": `"${version}"`,
                  "Idempotency-Key": body.client_change_id,
                },
              },
            },
          ),
        ),
      diff: async (ours: string, theirs: string) =>
        unwrapApiResult(
          await client.GET("/api/v1/projects/{project_id}/artifacts/{artifact_id}/diffs", {
            params: { ...params, query: { ours, theirs } },
          }),
        ),
      reconcile: async (body: components["schemas"]["ReconcileInput"]) =>
        unwrapApiResult(
          await client.POST("/api/v1/projects/{project_id}/artifacts/{artifact_id}/reconcile", {
            body,
            params,
          }),
        ),
      merge: async (version: number, body: components["schemas"]["MergeInput"]) =>
        unwrapApiResult(
          await client.POST("/api/v1/projects/{project_id}/artifacts/{artifact_id}/merge", {
            body,
            params: {
              ...params,
              header: {
                ...params.header,
                "If-Match": `"${version}"`,
                "Idempotency-Key": body.client_change_id,
              },
            },
          }),
        ),
    };
  }, [client, workspace, project, artifact]);
}
