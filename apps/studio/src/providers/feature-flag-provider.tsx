"use client";

import { createContext, useContext, type ReactNode } from "react";

export type FeatureFlag = "collaboration" | "knowledgeGraph" | "multimodal" | "workflowCanvas";
export type FeatureFlags = Readonly<Record<FeatureFlag, boolean>>;

export const disabledFeatureFlags: FeatureFlags = {
  collaboration: false,
  knowledgeGraph: false,
  multimodal: false,
  workflowCanvas: false,
};

const FeatureFlagContext = createContext<FeatureFlags>(disabledFeatureFlags);

export function FeatureFlagProvider({
  children,
  flags = disabledFeatureFlags,
}: {
  children: ReactNode;
  flags?: FeatureFlags;
}) {
  return <FeatureFlagContext.Provider value={flags}>{children}</FeatureFlagContext.Provider>;
}

export function useFeatureFlag(flag: FeatureFlag): boolean {
  return useContext(FeatureFlagContext)[flag];
}
