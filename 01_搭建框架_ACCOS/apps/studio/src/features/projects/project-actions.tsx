"use client";

import type { components } from "@accos/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@accos/ui";
import { useState } from "react";
import { InlineApiError } from "../../components/inline-api-error";
import { unwrapApiResult } from "../../lib/api/queries";
import { queryKeys } from "../../lib/api/query-keys";
import { useApiClient } from "../../providers/api-provider";
import { useIdentity } from "../../providers/identity-provider";
import { canWriteProjects } from "./permissions";

export function ProjectActions({ project }: { project: components["schemas"]["ProjectResponse"] }) {
  const identity = useIdentity();
  const client = useApiClient();
  const cache = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(project.name);
  const mutation = useMutation({
    mutationFn: async (archived: boolean) =>
      unwrapApiResult(
        await client.PUT("/api/v1/projects/{project_id}/details", {
          body: { name: editing ? name.trim() : project.name, archived },
          params: {
            path: { project_id: project.id },
            header: { "X-Workspace-ID": project.workspace_id, "If-Match": `"${project.version}"` },
          },
        }),
      ),
    onSuccess: async () => {
      setEditing(false);
      await cache.invalidateQueries({ queryKey: queryKeys.projects(project.workspace_id) });
    },
  });
  const canArchive = identity.permissions.includes("data:archive");
  return (
    <>
      {canWriteProjects(identity) ? (
        <div className="studio-action-row">
          {editing ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                mutation.mutate(project.status === "archived");
              }}
            >
              <label>
                项目名称
                <input
                  value={name}
                  maxLength={200}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </label>
              <Button type="submit" disabled={!name.trim()} busy={mutation.isPending}>
                保存名称
              </Button>
              <Button
                onClick={() => {
                  setEditing(false);
                  setName(project.name);
                }}
              >
                取消
              </Button>
            </form>
          ) : (
            <Button
              disabled={mutation.isPending || (project.status === "archived" && !canArchive)}
              onClick={() => {
                setName(project.name);
                setEditing(true);
              }}
            >
              改名
            </Button>
          )}
          {canArchive && !editing ? (
            <Button
              busy={mutation.isPending}
              onClick={() => mutation.mutate(project.status !== "archived")}
            >
              {project.status === "archived" ? "恢复项目" : "归档项目"}
            </Button>
          ) : null}
        </div>
      ) : null}
      {mutation.error ? (
        <>
          <InlineApiError error={mutation.error} title="项目未更新，名称仍保留" />
          <Button
            onClick={() =>
              void cache.invalidateQueries({ queryKey: queryKeys.projects(project.workspace_id) })
            }
          >
            刷新项目版本
          </Button>
        </>
      ) : null}
    </>
  );
}
