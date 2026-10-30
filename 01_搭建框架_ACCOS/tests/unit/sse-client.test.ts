import { describe, expect, it, vi } from "vitest";

import {
  createSseClient,
  createSseProjection,
  mergeSseEvent,
  parseSseStream,
  SseTransportError,
} from "../../packages/api-client/src/sse.ts";
import { createFixtureEvent, studioFixture } from "../fixtures/studio.ts";

function streamOf(...chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
}

describe("SSE transport", () => {
  it("parses a typed event split across chunks", async () => {
    const event = createFixtureEvent(2);
    const body = streamOf(
      `id: ${studioFixture.runId}:2\nevent: workflow.started\ndata: ${JSON.stringify(event).slice(0, 30)}`,
      `${JSON.stringify(event).slice(30)}\nretry: 15\n\n`,
    );

    const frames = [];
    for await (const frame of parseSseStream(body)) frames.push(frame);

    expect(frames).toEqual([{ event, id: `${studioFixture.runId}:2`, retry: 15 }]);
  });

  it("maps cursor expiry to a stable transport error", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "event_cursor_expired",
            correlation_id: studioFixture.eventId,
            message: "fixture-message",
            trace_id: studioFixture.eventId,
          },
        }),
        { status: 409 },
      ),
    );
    const client = createSseClient({
      baseUrl: "",
      fetch: fetcher,
      retryDelayMs: 1,
      token: studioFixture.token,
      workspaceId: studioFixture.workspaceId,
    });

    const iterator = client.stream({ runId: studioFixture.runId });
    await expect(iterator.next()).rejects.toMatchObject({
      code: "event_cursor_expired",
      status: 409,
    } satisfies Partial<SseTransportError>);
  });
});

describe("SSE projection", () => {
  it("deduplicates old events and resets on stream.reset", () => {
    const first = mergeSseEvent(createSseProjection(), createFixtureEvent(1));
    expect(mergeSseEvent(first, createFixtureEvent(1))).toBe(first);

    const reset = mergeSseEvent(first, createFixtureEvent(2, "stream.reset"));
    expect(reset).toMatchObject({ events: [], lastSequence: 2, resetRequired: true });
  });
});
