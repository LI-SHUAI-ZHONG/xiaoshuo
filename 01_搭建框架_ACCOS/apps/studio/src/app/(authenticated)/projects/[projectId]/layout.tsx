import type { ReactNode } from "react";

import { CurrentProjectProvider } from "../../../../providers/scope-providers";

export default async function CurrentProjectLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  return <CurrentProjectProvider projectId={projectId}>{children}</CurrentProjectProvider>;
}
