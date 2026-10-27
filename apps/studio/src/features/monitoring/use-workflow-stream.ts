"use client";

import {
  createSseClient,
  createSseProjection,
  mergeSseEvent,
  type SseConnectionState,
  type SseProjection,
} from "@accos/api-client";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { queryKeys } from "../../lib/api/query-keys";
import { useAuth } from "../../providers/auth-provider";
import { shouldResetWorkflowCursor } from "./status";

export function useWorkflowStream(workspaceId: string, runId: string, enabled = true) {
  const { session } = useAuth();
  const queryClient = useQueryClient();
  const cursorRef = useRef<string | undefined>(undefined);
  const [connectionState, setConnectionState] = useState<SseConnectionState>("connecting");
  const [cursorReset, setCursorReset] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [generation, setGeneration] = useState(0);
  const [projection, setProjection] = useState<SseProjection>(() => createSseProjection());

  useEffect(() => {
    cursorRef.current = undefined;
    setProjection(createSseProjection());
    setCursorReset(false);
    setError(null);
    setGeneration((value) => value + 1);
  }, [runId]);

  useEffect(() => {
    if (!enabled || !session || !workspaceId || !runId) return undefined;
    const controller = new AbortController();
    const stream = createSseClient({
      baseUrl: "",
      token: session.accessToken,
      workspaceId,
    });

    async function calibrateFromServer() {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.workflowRun(workspaceId, runId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.workflowSteps(workspaceId, runId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.workflowTasks(workspaceId, runId) }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.workflowApproval(workspaceId, runId),
        }),
      ]);
    }

    async function consume() {
      try {
        for await (const event of stream.stream({
          ...(cursorRef.current ? { lastEventId: cursorRef.current } : {}),
          onStateChange: setConnectionState,
          runId,
          signal: controller.signal,
        })) {
          setProjection((current) => {
            const next = mergeSseEvent(current, event);
            cursorRef.current = next.lastEventId ?? undefined;
            return next;
          });
          await calibrateFromServer();
        }
      } catch (streamError) {
        if (controller.signal.aborted) return;
        if (shouldResetWorkflowCursor(streamError)) {
          cursorRef.current = undefined;
          setCursorReset(true);
          setProjection({ ...createSseProjection(), resetRequired: true });
          setConnectionState("reconnecting");
          await calibrateFromServer();
          setGeneration((value) => value + 1);
          return;
        }
        setConnectionState("closed");
        setError(streamError);
      }
    }

    void consume();
    return () => {
      controller.abort();
    };
  }, [enabled, generation, queryClient, runId, session, workspaceId]);

  return {
    connectionState,
    cursorReset,
    error,
    projection,
    reconnect() {
      setError(null);
      setGeneration((value) => value + 1);
    },
  };
}
