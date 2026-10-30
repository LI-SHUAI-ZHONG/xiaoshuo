"use client";

import { useInfiniteQuery } from "@tanstack/react-query";
import { unwrapApiResult } from "../../lib/api/queries";
import { queryKeys } from "../../lib/api/query-keys";
import { useApiClient } from "../../providers/api-provider";

export function useProjectCatalog(workspace: string, query: string, archived: boolean) {
  const client = useApiClient();
  return useInfiniteQuery({
    queryKey: [...queryKeys.projects(workspace), "catalog", query, archived],
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) =>
      unwrapApiResult(
        await client.GET("/api/v1/workspaces/{workspace_id}/projects/page", {
          params: {
            path: { workspace_id: workspace },
            header: { "X-Workspace-ID": workspace },
            query: { query, archived, limit: 20, ...(pageParam ? { cursor: pageParam } : {}) },
          },
        }),
      ),
    getNextPageParam: (page) => page.next_cursor ?? undefined,
  });
}

export function useAssetCatalog(workspace: string, project: string, query: string) {
  const client = useApiClient();
  return useInfiniteQuery({
    queryKey: [...queryKeys.assets(workspace, project), "catalog", query],
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) =>
      unwrapApiResult(
        await client.GET("/api/v1/projects/{project_id}/assets/page", {
          params: {
            path: { project_id: project },
            header: { "X-Workspace-ID": workspace },
            query: { query, limit: 20, ...(pageParam ? { cursor: pageParam } : {}) },
          },
        }),
      ),
    getNextPageParam: (page) => page.next_cursor ?? undefined,
  });
}

export function useAssetHistory(workspace: string, project: string, asset: string) {
  const client = useApiClient();
  return useInfiniteQuery({
    queryKey: [...queryKeys.assets(workspace, project), asset, "history"],
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) =>
      unwrapApiResult(
        await client.GET("/api/v1/projects/{project_id}/assets/{asset_id}/versions", {
          params: {
            path: { project_id: project, asset_id: asset },
            header: { "X-Workspace-ID": workspace },
            query: { limit: 20, ...(pageParam ? { cursor: pageParam } : {}) },
          },
        }),
      ),
    getNextPageParam: (page) => page.next_cursor ?? undefined,
  });
}
