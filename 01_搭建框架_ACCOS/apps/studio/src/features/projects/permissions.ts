import type { components } from "@accos/api-client";

type Identity = components["schemas"]["IdentityMeResponse"];
type Project = components["schemas"]["ProjectResponse"];

export const PROJECT_WRITE_PERMISSION = "project:write";

export function canWriteProjects(identity: Identity): boolean {
  return identity.permissions.includes(PROJECT_WRITE_PERMISSION);
}

export function canWriteProject(identity: Identity, project: Project): boolean {
  return project.status === "active" && canWriteProjects(identity);
}
