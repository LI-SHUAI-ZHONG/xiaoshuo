import type { ReactNode } from "react";

import { WorkspaceProvider } from "../../../../providers/scope-providers";

export default async function WorkspaceLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ workspaceId: string }>;
}) {
  const { workspaceId } = await params;
  return <WorkspaceProvider workspaceId={workspaceId}>{children}</WorkspaceProvider>;
}
