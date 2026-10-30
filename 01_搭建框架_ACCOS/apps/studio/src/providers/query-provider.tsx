"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { ApiProblem } from "../lib/api/errors";

export function StudioQueryProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
            retry(failureCount, error) {
              if (
                error instanceof ApiProblem &&
                ["unauthenticated", "forbidden"].includes(error.kind)
              ) {
                return false;
              }
              return failureCount < 1;
            },
            staleTime: 15_000,
          },
        },
      }),
  );
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
