import type { components } from "./generated/schema.ts";

export type SseEventData = components["schemas"]["SseEventData"];

export type SseConnectionState = "connecting" | "open" | "reconnecting" | "closed";

export interface SseClientOptions {
  baseUrl: string;
  fetch?: typeof globalThis.fetch;
  retryDelayMs?: number;
  token: string;
  workspaceId: string;
}

export interface SseStreamOptions {
  lastEventId?: string;
  onStateChange?: (state: SseConnectionState) => void;
  runId: string;
  signal?: AbortSignal;
}

export interface SseProjection {
  events: readonly SseEventData[];
  lastEventId: string | null;
  lastSequence: number;
  resetRequired: boolean;
  runId: string | null;
}

export class SseTransportError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(message: string, status: number, code = "stream_error") {
    super(message);
    this.name = "SseTransportError";
    this.code = code;
    this.status = status;
  }
}

interface ParsedFrame {
  data: string;
  event?: string;
  id?: string;
  retry?: number;
}

function parseFrame(block: string): ParsedFrame | null {
  const data: string[] = [];
  let event: string | undefined;
  let id: string | undefined;
  let retry: number | undefined;

  for (const line of block.split(/\r?\n/)) {
    if (!line || line.startsWith(":")) continue;
    const separator = line.indexOf(":");
    const field = separator === -1 ? line : line.slice(0, separator);
    const rawValue = separator === -1 ? "" : line.slice(separator + 1);
    const value = rawValue.startsWith(" ") ? rawValue.slice(1) : rawValue;
    if (field === "data") data.push(value);
    if (field === "event") event = value;
    if (field === "id" && !value.includes("\0")) id = value;
    if (field === "retry" && /^\d+$/.test(value)) retry = Number(value);
  }

  if (data.length === 0) return null;
  return {
    data: data.join("\n"),
    ...(event === undefined ? {} : { event }),
    ...(id === undefined ? {} : { id }),
    ...(retry === undefined ? {} : { retry }),
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function isSseEventData(value: unknown): value is SseEventData {
  if (!isRecord(value)) return false;
  return (
    typeof value.correlation_id === "string" &&
    typeof value.event_id === "string" &&
    typeof value.occurred_at === "string" &&
    isRecord(value.payload) &&
    typeof value.project_id === "string" &&
    typeof value.run_id === "string" &&
    Number.isInteger(value.schema_version) &&
    Number.isInteger(value.sequence) &&
    typeof value.type === "string"
  );
}

export async function* parseSseStream(
  body: ReadableStream<Uint8Array>,
  signal?: AbortSignal,
): AsyncGenerator<{ event: SseEventData; id: string | null; retry: number | null }> {
  const decoder = new TextDecoder();
  const reader = body.getReader();
  let buffer = "";

  try {
    while (!signal?.aborted) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      const blocks = buffer.split(/\r?\n\r?\n/);
      buffer = blocks.pop() ?? "";
      for (const block of blocks) {
        const frame = parseFrame(block);
        if (!frame) continue;
        let parsed: unknown;
        try {
          parsed = JSON.parse(frame.data) as unknown;
        } catch {
          throw new SseTransportError("SSE 事件不是有效 JSON", 502, "invalid_event_data");
        }
        if (!isSseEventData(parsed)) {
          throw new SseTransportError(
            "SSE 事件不符合 SseEventData 契约",
            502,
            "invalid_event_data",
          );
        }
        yield { event: parsed, id: frame.id ?? null, retry: frame.retry ?? null };
      }
      if (done) break;
    }
  } finally {
    reader.releaseLock();
  }
}

function abortableDelay(milliseconds: number, signal?: AbortSignal): Promise<void> {
  if (signal?.aborted) return Promise.resolve();
  return new Promise((resolve) => {
    const timeout = setTimeout(resolve, milliseconds);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timeout);
        resolve();
      },
      { once: true },
    );
  });
}

async function getErrorCode(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as unknown;
    if (isRecord(payload) && isRecord(payload.error) && typeof payload.error.code === "string") {
      return payload.error.code;
    }
  } catch {
    // The stable status remains useful when a proxy strips the error body.
  }
  return "stream_error";
}

export function createSseClient(options: SseClientOptions) {
  const fetcher = options.fetch ?? globalThis.fetch;
  const initialRetry = options.retryDelayMs ?? 3000;
  const baseUrl = options.baseUrl.replace(/\/$/, "");

  return {
    async *stream({
      lastEventId,
      onStateChange,
      runId,
      signal,
    }: SseStreamOptions): AsyncGenerator<SseEventData> {
      let cursor = lastEventId;
      let retryDelay = initialRetry;
      let connected = false;

      while (!signal?.aborted) {
        onStateChange?.(connected ? "reconnecting" : "connecting");
        let response: Response;
        try {
          response = await fetcher(`${baseUrl}/api/v1/events?run_id=${encodeURIComponent(runId)}`, {
            headers: {
              Accept: "text/event-stream",
              ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
              ...(cursor ? { "Last-Event-ID": cursor } : {}),
              "X-Workspace-ID": options.workspaceId,
            },
            ...(signal ? { signal } : {}),
          });
        } catch {
          if (signal?.aborted) break;
          connected = true;
          await abortableDelay(retryDelay, signal);
          continue;
        }

        if (!response.ok) {
          const code = await getErrorCode(response);
          throw new SseTransportError(
            `SSE 请求失败（${String(response.status)}）`,
            response.status,
            code,
          );
        }
        if (!response.body) {
          throw new SseTransportError("SSE 响应缺少可读数据流", 502, "missing_stream_body");
        }

        connected = true;
        onStateChange?.("open");
        for await (const frame of parseSseStream(response.body, signal)) {
          if (frame.id) cursor = frame.id;
          if (frame.retry !== null) retryDelay = frame.retry;
          yield frame.event;
        }
        if (!signal?.aborted) await abortableDelay(retryDelay, signal);
      }
      onStateChange?.("closed");
    },
  };
}

export function createSseProjection(): SseProjection {
  return {
    events: [],
    lastEventId: null,
    lastSequence: -1,
    resetRequired: false,
    runId: null,
  };
}

export function mergeSseEvent(state: SseProjection, event: SseEventData): SseProjection {
  if (state.runId !== null && state.runId !== event.run_id) return state;
  if (event.type === "stream.reset") {
    return {
      events: [],
      lastEventId: `${event.run_id}:${String(event.sequence)}`,
      lastSequence: event.sequence,
      resetRequired: true,
      runId: event.run_id,
    };
  }
  if (event.sequence <= state.lastSequence) return state;
  return {
    events: [...state.events, event],
    lastEventId: `${event.run_id}:${String(event.sequence)}`,
    lastSequence: event.sequence,
    resetRequired: false,
    runId: event.run_id,
  };
}
