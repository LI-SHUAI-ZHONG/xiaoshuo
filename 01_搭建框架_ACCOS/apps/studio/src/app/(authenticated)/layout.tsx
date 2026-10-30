import type { ReactNode } from "react";

import { AppShell } from "../../components/app-shell";
import { AuthenticatedBoundary } from "../../providers/identity-provider";

export default function AuthenticatedLayout({ children }: { children: ReactNode }) {
  return (
    <AuthenticatedBoundary>
      <AppShell>{children}</AppShell>
    </AuthenticatedBoundary>
  );
}
