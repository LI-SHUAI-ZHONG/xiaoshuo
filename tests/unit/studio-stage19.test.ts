import type { components } from "../../packages/api-client/src/index.ts";
import { describe, expect, it } from "vitest";

import {
  canWriteProject,
  canWriteProjects,
} from "../../apps/studio/src/features/projects/permissions.ts";

type Identity = components["schemas"]["IdentityMeResponse"];
type Project = components["schemas"]["ProjectResponse"];

const identity: Identity = {
  actor_id: "11111111-1111-4111-8111-111111111111",
  actor_kind: "user",
  auth_method: "legacy",
  permissions: ["project:read", "project:write"],
  policy_version: "rbac.v1",
  workspace_id: "22222222-2222-4222-8222-222222222222",
};

const project: Project = {
  archived_at: null,
  created_at: "2026-09-07T00:00:00Z",
  created_by: identity.actor_id,
  id: "33333333-3333-4333-8333-333333333333",
  name: "fixture-project",
  settings: { asset_retention_days: 30, revision_retention_limit: 100 },
  status: "active",
  updated_at: "2026-09-07T00:00:00Z",
  version: 1,
  workspace_id: identity.workspace_id,
};

describe("Studio stage 19 permission projection", () => {
  it("shows project writes only when the server snapshot grants project:write", () => {
    expect(canWriteProjects(identity)).toBe(true);
    expect(canWriteProjects({ ...identity, permissions: ["project:read"] })).toBe(false);
  });

  it("keeps archived projects read-only even for a writer", () => {
    expect(canWriteProject(identity, project)).toBe(true);
    expect(canWriteProject(identity, { ...project, status: "archived" })).toBe(false);
  });
});
