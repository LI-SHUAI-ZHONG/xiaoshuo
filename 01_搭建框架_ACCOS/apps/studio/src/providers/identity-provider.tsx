"use client";

import type { components } from "@accos/api-client";
import { createContext, useContext, type ReactNode } from "react";

import { StateResolver } from "../components/state-resolver";
import { asApiProblem } from "../lib/api/errors";
import { useIdentityQuery } from "../lib/api/queries";
import { useAuth } from "./auth-provider";

type Identity = components["schemas"]["IdentityMeResponse"];

const IdentityContext = createContext<Identity | null>(null);

function VerifiedIdentity({ children }: { children: ReactNode }) {
  const query = useIdentityQuery();
  if (query.isPending) return <StateResolver state="loading" />;
  if (query.isError && (!query.data || asApiProblem(query.error).kind !== "offline"))
    return <StateResolver error={query.error} onRetry={() => void query.refetch()} />;
  return <IdentityContext.Provider value={query.data ?? null}>{children}</IdentityContext.Provider>;
}

export function AuthenticatedBoundary({ children }: { children: ReactNode }) {
  const { session, loading } = useAuth();
  if (loading) return <StateResolver state="loading" />;
  if (!session) return <StateResolver state="unauthenticated" />;
  return <VerifiedIdentity>{children}</VerifiedIdentity>;
}

export function useIdentity(): Identity {
  const value = useContext(IdentityContext);
  if (!value) throw new Error("useIdentity must be used within AuthenticatedBoundary");
  return value;
}
