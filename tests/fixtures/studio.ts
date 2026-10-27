import type { SseEventData } from "../../packages/api-client/src/sse.ts";

export const studioFixture = {
  actorId: "11111111-1111-4111-8111-111111111111",
  eventId: "44444444-4444-4444-8444-444444444444",
  projectId: "33333333-3333-4333-8333-333333333333",
  runId: "55555555-5555-4555-8555-555555555555",
  token: "fixture-token-value",
  workspaceId: "22222222-2222-4222-8222-222222222222",
} as const;

export function createFixtureEvent(sequence = 0, type = "workflow.started"): SseEventData {
  return {
    correlation_id: studioFixture.eventId,
    event_id: studioFixture.eventId,
    occurred_at: "2026-01-01T00:00:00Z",
    payload: {},
    project_id: studioFixture.projectId,
    run_id: studioFixture.runId,
    schema_version: 1,
    sequence,
    type,
  };
}
