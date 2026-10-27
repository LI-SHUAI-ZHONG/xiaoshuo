"use client";

import { ErrorState } from "@accos/ui";

import { asApiProblem } from "../lib/api/errors";

export function InlineApiError({ error, title }: { error: unknown; title: string }) {
  const problem = asApiProblem(error);
  return (
    <ErrorState
      correlationId={problem.correlationId ?? undefined}
      description={problem.message}
      title={title}
    />
  );
}
