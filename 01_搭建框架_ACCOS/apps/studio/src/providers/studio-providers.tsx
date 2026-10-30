"use client";

import type { ReactNode } from "react";

import { ApiProvider } from "./api-provider";
import { AuthProvider, type AuthSession } from "./auth-provider";
import {
  disabledFeatureFlags,
  FeatureFlagProvider,
  type FeatureFlags,
} from "./feature-flag-provider";
import { StudioQueryProvider } from "./query-provider";

export function StudioProviders({
  children,
  flags = disabledFeatureFlags,
  initialSession = null,
}: {
  children: ReactNode;
  flags?: FeatureFlags;
  initialSession?: AuthSession | null;
}) {
  return (
    <FeatureFlagProvider flags={flags}>
      <StudioQueryProvider>
        <AuthProvider initialSession={initialSession}>
          <ApiProvider>{children}</ApiProvider>
        </AuthProvider>
      </StudioQueryProvider>
    </FeatureFlagProvider>
  );
}
