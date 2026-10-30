import { SseTransportError, type components } from "@accos/api-client";

type Identity = components["schemas"]["IdentityMeResponse"];
type BadgeTone = "danger" | "info" | "neutral" | "success" | "warning";

const successStatuses = new Set([
  "active",
  "alive",
  "approved",
  "applied",
  "available",
  "completed",
  "configured",
  "enabled",
  "healthy",
  "passed",
  "ready",
  "registered",
  "succeeded",
  "verified",
]);
const dangerStatuses = new Set([
  "budget_exhausted",
  "cancelled",
  "critical",
  "dead_letter",
  "failed",
  "limit_exceeded",
  "not_ready",
  "open",
  "rejected",
  "run_failed",
  "unavailable",
]);
const warningStatuses = new Set([
  "cancelling",
  "degraded",
  "expired",
  "findings",
  "not_configured",
  "paused",
  "stopped",
  "waiting_approval",
  "withdrawn",
]);
const infoStatuses = new Set([
  "connecting",
  "pending",
  "planned",
  "proposed",
  "reconnecting",
  "running",
]);
const cursorResetCodes = new Set(["event_cursor_expired", "invalid_event_data"]);

export const terminalWorkflowStatuses = new Set(["cancelled", "failed", "succeeded"]);

export function toneForStatus(status: string): BadgeTone {
  const normalized = status.toLowerCase();
  if (successStatuses.has(normalized)) return "success";
  if (dangerStatuses.has(normalized)) return "danger";
  if (warningStatuses.has(normalized)) return "warning";
  if (infoStatuses.has(normalized)) return "info";
  return "neutral";
}

export function hasPermission(identity: Identity, permission: string): boolean {
  return identity.permissions.includes(permission);
}

export function canOperateProject(identity: Identity, projectStatus: string): boolean {
  return projectStatus === "active" && hasPermission(identity, "project:write");
}

export function canRunAgents(identity: Identity, projectStatus: string): boolean {
  return projectStatus === "active" && hasPermission(identity, "agent:run");
}

export function canDecideApprovals(identity: Identity): boolean {
  return identity.actor_kind === "user" && hasPermission(identity, "approval:decide");
}

export function isWorkflowTerminal(status: string): boolean {
  return terminalWorkflowStatuses.has(status);
}

export function operationalState(
  readiness: "not_ready" | "ready",
  checks: readonly { status: string }[],
): "degraded" | "not_ready" | "ready" {
  if (readiness === "not_ready") return "not_ready";
  return checks.some((check) => check.status !== "healthy") ? "degraded" : "ready";
}

export function shouldResetWorkflowCursor(error: unknown): boolean {
  return error instanceof SseTransportError && cursorResetCodes.has(error.code);
}
