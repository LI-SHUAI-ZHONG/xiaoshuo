"use client";

import type { components } from "@accos/api-client";
import { createContext, useContext, type ReactNode } from "react";

import { StateResolver } from "../components/state-resolver";
import { asApiProblem } from "../lib/api/errors";
import { useProjectQuery, useWorkspaceQuery } from "../lib/api/queries";
import { useIdentity } from "./identity-provider";

type Project = components["schemas"]["ProjectResponse"];
type Workspace = components["schemas"]["WorkspaceResponse"];

const WorkspaceContext = createContext<Workspace | null>(null);
const ProjectContext = createContext<Project | null>(null);

export function WorkspaceProvider({
  children,
  workspaceId,
}: {
  children: ReactNode;
  workspaceId: string;
}) {
  const query = useWorkspaceQuery(workspaceId);
  if (query.isPending) return <StateResolver state="loading" />;
  if (query.isError && (!query.data || asApiProblem(query.error).kind !== "offline"))
    return <StateResolver error={query.error} onRetry={() => void query.refetch()} />;
  return (
    <WorkspaceContext.Provider value={query.data ?? null}>{children}</WorkspaceContext.Provider>
  );
}

export function ProjectProvider({
  children,
  projectId,
  workspaceId,
}: {
  children: ReactNode;
  projectId: string;
  workspaceId: string;
}) {
  const query = useProjectQuery(workspaceId, projectId);
  if (query.isPending) return <StateResolver state="loading" />;
  if (query.isError && (!query.data || asApiProblem(query.error).kind !== "offline"))
    return <StateResolver error={query.error} onRetry={() => void query.refetch()} />;
  if (!query.data || query.data.workspace_id !== workspaceId)
    return <StateResolver state="forbidden" />;
  return <ProjectContext.Provider value={query.data}>{children}</ProjectContext.Provider>;
}

export function CurrentProjectProvider({
  children,
  projectId,
}: {
  children: ReactNode;
  projectId: string;
}) {
  const identity = useIdentity();
  return (
    <WorkspaceProvider workspaceId={identity.workspace_id}>
      <ProjectProvider projectId={projectId} workspaceId={identity.workspace_id}>
        {children}
      </ProjectProvider>
    </WorkspaceProvider>
  );
}

export function useWorkspace(): Workspace {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("useWorkspace must be used within WorkspaceProvider");
  return value;
}

export function useProject(): Project {
  const value = useContext(ProjectContext);
  if (!value) throw new Error("useProject must be used within ProjectProvider");
  return value;
}
