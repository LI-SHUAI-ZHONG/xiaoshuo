import type { ReactNode } from "react";

import { ProjectProvider } from "../../../../../../providers/scope-providers";

export default async function ProjectLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ projectId: string; workspaceId: string }>;
}) {
  const { projectId, workspaceId } = await params;
  return (
    <ProjectProvider projectId={projectId} workspaceId={workspaceId}>
      {children}
    </ProjectProvider>
  );
}
