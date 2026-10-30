import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import type { components } from "../../packages/api-client/src/index.ts";
import { SseTransportError } from "../../packages/api-client/src/index.ts";
import { describe, expect, it } from "vitest";

import {
  canDecideApprovals,
  canRunAgents,
  isWorkflowTerminal,
  operationalState,
  shouldResetWorkflowCursor,
  toneForStatus,
} from "../../apps/studio/src/features/monitoring/status.ts";

type Identity = components["schemas"]["IdentityMeResponse"];

const repositoryRoot = resolve(import.meta.dirname, "../..");
const owner: Identity = {
  actor_id: "11111111-1111-4111-8111-111111111111",
  actor_kind: "user",
  auth_method: "legacy",
  permissions: ["project:read", "project:write", "agent:run", "approval:decide"],
  policy_version: "rbac.v1",
  workspace_id: "22222222-2222-4222-8222-222222222222",
};

describe("Studio stage 20 state projection", () => {
  it("keeps write and approval controls bound to the server permission snapshot", () => {
    expect(canRunAgents(owner, "active")).toBe(true);
    expect(canRunAgents(owner, "archived")).toBe(false);
    expect(canDecideApprovals(owner)).toBe(true);
    expect(
      canDecideApprovals({ ...owner, permissions: ["project:read"], actor_kind: "service" }),
    ).toBe(false);
  });

  it("distinguishes terminal, degraded, and not-configured states", () => {
    expect(isWorkflowTerminal("succeeded")).toBe(true);
    expect(isWorkflowTerminal("waiting_approval")).toBe(false);
    expect(toneForStatus("not_configured")).toBe("warning");
    expect(operationalState("ready", [{ status: "degraded" }])).toBe("degraded");
    expect(operationalState("not_ready", [{ status: "healthy" }])).toBe("not_ready");
  });

  it("resets expired or invalid SSE cursors before status recalibration", () => {
    expect(
      shouldResetWorkflowCursor(new SseTransportError("expired", 409, "event_cursor_expired")),
    ).toBe(true);
    expect(
      shouldResetWorkflowCursor(new SseTransportError("denied", 403, "permission_denied")),
    ).toBe(false);
  });

  it("declares every stage 20 route without browser-persisted server truth", () => {
    const routeFiles = [
      "apps/studio/src/app/(authenticated)/projects/[projectId]/workflows/page.tsx",
      "apps/studio/src/app/(authenticated)/projects/[projectId]/workflows/runs/[runId]/page.tsx",
      "apps/studio/src/app/(authenticated)/projects/[projectId]/agents/page.tsx",
      "apps/studio/src/app/(authenticated)/projects/[projectId]/quality/page.tsx",
      "apps/studio/src/app/(authenticated)/feedback/page.tsx",
      "apps/studio/src/app/(authenticated)/system/page.tsx",
      "apps/studio/src/app/(authenticated)/settings/page.tsx",
    ];
    for (const file of routeFiles) {
      expect(() => readFileSync(resolve(repositoryRoot, file), "utf8")).not.toThrow();
    }

    const stage20Source = [
      "apps/studio/src/features/workflows/workflow-run-detail.tsx",
      "apps/studio/src/features/agents/agent-center.tsx",
      "apps/studio/src/features/feedback/feedback-workspace.tsx",
    ]
      .map((file) => readFileSync(resolve(repositoryRoot, file), "utf8"))
      .join("\n");
    expect(stage20Source).not.toMatch(/localStorage|sessionStorage/);
    expect(stage20Source).not.toContain("Agent 在线");
  });
});
