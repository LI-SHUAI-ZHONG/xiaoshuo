import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const repositoryRoot = resolve(import.meta.dirname, "../..");

function read(path: string): string {
  return readFileSync(resolve(repositoryRoot, path), "utf8");
}

describe("Studio route and state boundaries", () => {
  it("uses App Router project parameters and public/authenticated groups", () => {
    const routeFiles = [
      "apps/studio/src/app/(public)/status/page.tsx",
      "apps/studio/src/app/(authenticated)/workspaces/page.tsx",
      "apps/studio/src/app/(authenticated)/workspaces/[workspaceId]/page.tsx",
      "apps/studio/src/app/(authenticated)/workspaces/[workspaceId]/projects/[projectId]/page.tsx",
      "apps/studio/src/app/(authenticated)/dashboard/page.tsx",
      "apps/studio/src/app/(authenticated)/projects/page.tsx",
      "apps/studio/src/app/(authenticated)/projects/[projectId]/page.tsx",
      "apps/studio/src/app/(authenticated)/projects/[projectId]/knowledge/page.tsx",
      "apps/studio/src/app/(authenticated)/projects/[projectId]/memory/page.tsx",
      "apps/studio/src/app/(authenticated)/projects/[projectId]/write/[artifactId]/page.tsx",
      "apps/studio/src/app/(authenticated)/projects/[projectId]/workflows/page.tsx",
      "apps/studio/src/app/(authenticated)/projects/[projectId]/workflows/runs/[runId]/page.tsx",
      "apps/studio/src/app/(authenticated)/projects/[projectId]/agents/page.tsx",
      "apps/studio/src/app/(authenticated)/projects/[projectId]/quality/page.tsx",
      "apps/studio/src/app/(authenticated)/feedback/page.tsx",
      "apps/studio/src/app/(authenticated)/system/page.tsx",
      "apps/studio/src/app/(authenticated)/settings/page.tsx",
    ];
    for (const file of routeFiles) expect(() => read(file)).not.toThrow();
    expect(routeFiles.join("\n")).not.toContain(":id");
  });

  it("keeps server data in Query Cache and local layout state in Zustand", () => {
    const queries = read("apps/studio/src/lib/api/queries.ts");
    const store = read("apps/studio/src/stores/ui-store.ts");
    expect(queries).toContain("useQuery");
    expect(queries).toContain("@accos/api-client");
    expect(store).toContain("sidebarOpen");
    expect(store).toContain("draftPanelWidth");
    expect(store).not.toContain("workspaceItems");
    expect(store).not.toContain("projects");
  });

  it("does not bypass the generated client or embed an absolute API URL", () => {
    const queries = read("apps/studio/src/lib/api/queries.ts");
    const mutations = read("apps/studio/src/lib/api/mutations.ts");
    const apiProvider = read("apps/studio/src/providers/api-provider.tsx");
    const nextConfig = read("apps/studio/next.config.ts");
    expect(queries).not.toContain("fetch(");
    expect(mutations).not.toContain("fetch(");
    expect(apiProvider).toContain("createAccosClient");
    expect(`${queries}${mutations}${apiProvider}${nextConfig}`).not.toMatch(/https?:\/\//);
  });

  it("declares focus and responsive behavior", () => {
    const uiStyles = read("packages/ui/src/styles.css");
    const appStyles = read("apps/studio/src/app/globals.css");
    expect(uiStyles).toContain(":focus-visible");
    expect(uiStyles).toContain("prefers-reduced-motion");
    expect(appStyles).toContain("@media (max-width: 52rem)");
  });
});
