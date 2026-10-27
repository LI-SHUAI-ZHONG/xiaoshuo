import createClient from "openapi-fetch";

import type { paths } from "./generated/schema.ts";

export interface AccosClientOptions {
  baseUrl: string;
  token: string;
  csrfToken?: string;
  workspaceId: string;
  fetch?: typeof globalThis.fetch;
}

export function createAccosClient(options: AccosClientOptions) {
  const common = {
    baseUrl: options.baseUrl,
    credentials: "same-origin" as const,
    headers: {
      ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
      ...(options.csrfToken ? { "X-CSRF-Token": options.csrfToken } : {}),
      "X-Workspace-ID": options.workspaceId,
    },
  };
  if (options.fetch) return createClient<paths>({ ...common, fetch: options.fetch });
  return createClient<paths>(common);
}

export function createAuthClient() {
  return createClient<paths>({ baseUrl: "", credentials: "same-origin" });
}
