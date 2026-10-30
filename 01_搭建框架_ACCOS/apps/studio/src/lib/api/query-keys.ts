export const queryKeys = {
  agentRun: (workspaceId: string, runId: string) =>
    ["workspaces", workspaceId, "agent-runs", runId] as const,
  agents: (workspaceId: string) => ["workspaces", workspaceId, "agents"] as const,
  artifact: (workspaceId: string, projectId: string, artifactId: string) =>
    ["workspaces", workspaceId, "projects", projectId, "artifacts", artifactId] as const,
  artifacts: (workspaceId: string, projectId: string) =>
    ["workspaces", workspaceId, "projects", projectId, "artifacts"] as const,
  assets: (workspaceId: string, projectId: string) =>
    ["workspaces", workspaceId, "projects", projectId, "assets"] as const,
  health: (workspaceId: string) => ["system", "health", workspaceId] as const,
  systemSettings: (workspaceId: string) => ["system", "settings", workspaceId] as const,
  identity: (workspaceId: string) => ["identity", workspaceId] as const,
  ingestionRun: (workspaceId: string, runId: string) =>
    ["workspaces", workspaceId, "knowledge", "ingestion-runs", runId] as const,
  memory: (workspaceId: string, projectId: string, memoryId: string) =>
    ["workspaces", workspaceId, "projects", projectId, "memories", memoryId] as const,
  project: (workspaceId: string, projectId: string) =>
    ["workspaces", workspaceId, "projects", projectId] as const,
  projects: (workspaceId: string) => ["workspaces", workspaceId, "projects"] as const,
  revisions: (workspaceId: string, projectId: string, artifactId: string) =>
    [
      "workspaces",
      workspaceId,
      "projects",
      projectId,
      "artifacts",
      artifactId,
      "revisions",
    ] as const,
  workspace: (workspaceId: string) => ["workspaces", workspaceId] as const,
  workspaces: (workspaceId: string) => ["workspaces", { scope: workspaceId }] as const,
  workflowApproval: (workspaceId: string, runId: string) =>
    ["workspaces", workspaceId, "workflow-runs", runId, "approval"] as const,
  workflowDefinitions: (workspaceId: string) =>
    ["workspaces", workspaceId, "workflows", "definitions"] as const,
  workflowRun: (workspaceId: string, runId: string) =>
    ["workspaces", workspaceId, "workflow-runs", runId] as const,
  workflowSteps: (workspaceId: string, runId: string) =>
    ["workspaces", workspaceId, "workflow-runs", runId, "steps"] as const,
  workflowTasks: (workspaceId: string, runId: string) =>
    ["workspaces", workspaceId, "workflow-runs", runId, "tasks"] as const,
  modelStatus: (workspaceId: string) => ["workspaces", workspaceId, "models", "status"] as const,
  toolStatus: (workspaceId: string) => ["workspaces", workspaceId, "tools", "status"] as const,
  behaviorConsent: (workspaceId: string, projectId: string) =>
    ["workspaces", workspaceId, "projects", projectId, "behavior-consent"] as const,
  consistencyCheck: (workspaceId: string, projectId: string, runId: string) =>
    ["workspaces", workspaceId, "projects", projectId, "consistency-checks", runId] as const,
  consistencyResolution: (workspaceId: string, projectId: string, proposalId: string) =>
    [
      "workspaces",
      workspaceId,
      "projects",
      projectId,
      "consistency-resolutions",
      proposalId,
    ] as const,
  diagnostic: (workspaceId: string, projectId: string, findingId: string) =>
    ["workspaces", workspaceId, "projects", projectId, "diagnostics", findingId] as const,
  experiment: (workspaceId: string, projectId: string, experimentId: string) =>
    ["workspaces", workspaceId, "projects", projectId, "experiments", experimentId] as const,
  feedback: (workspaceId: string, projectId: string, eventId: string) =>
    ["workspaces", workspaceId, "projects", projectId, "feedback", eventId] as const,
  improvementProposal: (workspaceId: string, projectId: string, proposalId: string) =>
    [
      "workspaces",
      workspaceId,
      "projects",
      projectId,
      "improvement-proposals",
      proposalId,
    ] as const,
  metricPoint: (workspaceId: string, projectId: string, pointId: string) =>
    ["workspaces", workspaceId, "projects", projectId, "metric-points", pointId] as const,
  qualityEvaluation: (workspaceId: string, projectId: string, runId: string) =>
    ["workspaces", workspaceId, "projects", projectId, "quality-evaluations", runId] as const,
};
