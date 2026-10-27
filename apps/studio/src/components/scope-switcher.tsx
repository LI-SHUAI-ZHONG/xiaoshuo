"use client";

import { Select, Skeleton } from "@accos/ui";
import { useParams, useRouter } from "next/navigation";

import { useProjectsQuery, useWorkspacesQuery } from "../lib/api/queries";
import { useAuth } from "../providers/auth-provider";

function routeParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export function ScopeSwitcher() {
  const params = useParams();
  const router = useRouter();
  const { session, setSession, info } = useAuth();
  const workspaceId = routeParam(params.workspaceId) ?? session?.workspaceId;
  const projectId = routeParam(params.projectId);
  const workspaces = useWorkspacesQuery();
  const projects = useProjectsQuery(workspaceId ?? "");
  const workspaceItems =
    info?.workspaces?.map((w) => ({ id: w.id, name: w.name })) ??
    workspaces.data?.items.map((w) => ({ id: w.id, name: w.id })) ??
    [];
  const projectItems = projects.data?.items ?? [];

  if (workspaces.isPending) return <Skeleton label="正在加载作用域" lines={1} />;

  return (
    <div className="studio-scope-switcher">
      <Select
        aria-label="切换 Workspace"
        disabled={workspaces.isError || workspaceItems.length === 0}
        label="Workspace"
        onChange={(event) => {
          if (session) setSession({ ...session, workspaceId: event.target.value });
          router.push("/dashboard");
        }}
        value={workspaceId ?? ""}
      >
        <option disabled value="">
          选择 Workspace
        </option>
        {workspaceItems.map((workspace) => (
          <option key={workspace.id} value={workspace.id}>
            {workspace.name}
          </option>
        ))}
      </Select>
      {workspaceId ? (
        <Select
          aria-label="切换 Project"
          disabled={projects.isPending || projects.isError || projectItems.length === 0}
          label="Project"
          onChange={(event) => {
            router.push(`/projects/${encodeURIComponent(event.target.value)}`);
          }}
          value={projectId ?? ""}
        >
          <option disabled value="">
            选择 Project
          </option>
          {projectItems.map((project) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </Select>
      ) : null}
    </div>
  );
}
