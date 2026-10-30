"use client";

import { createAccosClient } from "@accos/api-client";
import { createContext, useContext, useMemo, type ReactNode } from "react";

import { useAuth } from "./auth-provider";

type AccosClient = ReturnType<typeof createAccosClient>;

const ApiContext = createContext<AccosClient | null>(null);

export function ApiProvider({ children }: { children: ReactNode }) {
  const { session } = useAuth();
  const client = useMemo(
    () =>
      session
        ? createAccosClient({
            baseUrl: "",
            token: session.accessToken,
            ...(session.csrfToken ? { csrfToken: session.csrfToken } : {}),
            workspaceId: session.workspaceId,
          })
        : null,
    [session],
  );
  return <ApiContext.Provider value={client}>{children}</ApiContext.Provider>;
}

export function useApiClient(): AccosClient {
  const client = useContext(ApiContext);
  if (!client) throw new Error("An authenticated API client is required");
  return client;
}
