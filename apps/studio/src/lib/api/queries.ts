"use client";

import type { components } from "@accos/api-client";
import { useQuery } from "@tanstack/react-query";

import { mapApiError } from "./errors";
import { queryKeys } from "./query-keys";
import { useApiClient } from "../../providers/api-provider";
import { useAuth } from "../../providers/auth-provider";

type Identity = components["schemas"]["IdentityMeResponse"];
type AgentCollection = components["schemas"]["AgentCollectionResponse"];
type AgentRun = components["schemas"]["AgentRunResponse"];
type Approval = components["schemas"]["ApprovalResponse"];
type Artifact = components["schemas"]["ArtifactResponse"];
type ArtifactCollection = components["schemas"]["ArtifactCollectionResponse"];
type AssetCollection = components["schemas"]["AssetCollectionResponse"];
type BehaviorConsentStatus = components["schemas"]["BehaviorConsentStatusResponse"];
type ConsistencyCheck = components["schemas"]["ConsistencyCheckResponse"];
type Diagnostic = components["schemas"]["DiagnosticResponse"];
type Experiment = components["schemas"]["ExperimentResponse"];
type Feedback = components["schemas"]["FeedbackResponse"];
type IngestionRun = components["schemas"]["IngestionRunResponse"];
type Memory = components["schemas"]["MemoryResponse"];
type ImprovementProposal = components["schemas"]["ImprovementProposalResponse"];
type MetricPoint = components["schemas"]["MetricPointResponse"];
type ModelStatus = components["schemas"]["ModelStatusResponse"];
type Project = components["schemas"]["ProjectResponse"];
type ProjectCollection = components["schemas"]["ProjectCollectionResponse"];
type RevisionCollection = components["schemas"]["RevisionCollectionResponse"];
type Resolution = components["schemas"]["ResolutionResponse"];
type QualityResult = components["schemas"]["QualityResultResponse"];
type StepRunCollection = components["schemas"]["StepRunCollectionResponse"];
type SystemHealth = components["schemas"]["SystemHealthResponse"];
type SystemSettings = components["schemas"]["SystemSettingsResponse"];
type TaskRunCollection = components["schemas"]["TaskRunCollectionResponse"];
type ToolStatus = components["schemas"]["ToolStatusResponse"];
type WorkflowDefinitionCollection = components["schemas"]["WorkflowDefinitionCollectionResponse"];
type WorkflowRun = components["schemas"]["WorkflowRunResponse"];
type Workspace = components["schemas"]["WorkspaceResponse"];
type WorkspaceCollection = components["schemas"]["WorkspaceCollectionResponse"];

export function unwrapApiResult<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.data !== undefined) return result.data;
  throw mapApiError(result.error, result.response);
}

function isSystemHealth(value: unknown): value is SystemHealth {
  return (
    typeof value === "object" &&
    value !== null &&
    "status" in value &&
    (value.status === "ready" || value.status === "not_ready") &&
    "checks" in value &&
    Array.isArray(value.checks)
  );
}

function unwrapSystemHealth(result: {
  data?: SystemHealth;
  error?: unknown;
  response: Response;
}): SystemHealth {
  if (result.data !== undefined) return result.data;
  if (result.response.status === 503 && isSystemHealth(result.error)) return result.error;
  throw mapApiError(result.error, result.response);
}

export function useIdentityQuery() {
  const client = useApiClient();
  const { session } = useAuth();
  const workspaceId = session?.workspaceId ?? "";
  return useQuery<Identity>({
    queryKey: queryKeys.identity(workspaceId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/identity/me", {
          params: { header: { "X-Workspace-ID": workspaceId } },
        }),
      ),
  });
}

export function useHealthQuery() {
  const client = useApiClient();
  const { session } = useAuth();
  const workspaceId = session?.workspaceId ?? "";
  return useQuery<SystemHealth>({
    queryKey: queryKeys.health(workspaceId),
    queryFn: async () =>
      unwrapSystemHealth(
        await client.GET("/api/v1/system/health", {
          params: { header: { "X-Workspace-ID": workspaceId } },
        }),
      ),
    refetchInterval: 30_000,
  });
}

export function useSystemSettingsQuery() {
  const client = useApiClient();
  const { session } = useAuth();
  const workspaceId = session?.workspaceId ?? "";
  return useQuery<SystemSettings>({
    queryKey: queryKeys.systemSettings(workspaceId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/system/settings", {
          params: { header: { "X-Workspace-ID": workspaceId } },
        }),
      ),
    refetchInterval: 30_000,
  });
}

export function useWorkflowDefinitionsQuery() {
  const client = useApiClient();
  const { session } = useAuth();
  const workspaceId = session?.workspaceId ?? "";
  return useQuery<WorkflowDefinitionCollection>({
    queryKey: queryKeys.workflowDefinitions(workspaceId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/workflows", {
          params: { header: { "X-Workspace-ID": workspaceId } },
        }),
      ),
  });
}

const terminalWorkflowStatuses = new Set(["succeeded", "failed", "cancelled"]);

export function useWorkflowRunQuery(workspaceId: string, runId: string) {
  const client = useApiClient();
  return useQuery<WorkflowRun>({
    enabled: Boolean(workspaceId && runId),
    queryKey: queryKeys.workflowRun(workspaceId, runId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/workflow-runs/{run_id}", {
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { run_id: runId },
          },
        }),
      ),
    refetchInterval: (query) =>
      query.state.data && terminalWorkflowStatuses.has(query.state.data.status) ? false : 2_000,
  });
}

export function useWorkflowStepsQuery(workspaceId: string, runId: string) {
  const client = useApiClient();
  return useQuery<StepRunCollection>({
    enabled: Boolean(workspaceId && runId),
    queryKey: queryKeys.workflowSteps(workspaceId, runId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/workflow-runs/{run_id}/steps", {
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { run_id: runId },
          },
        }),
      ),
  });
}

export function useWorkflowTasksQuery(workspaceId: string, runId: string) {
  const client = useApiClient();
  return useQuery<TaskRunCollection>({
    enabled: Boolean(workspaceId && runId),
    queryKey: queryKeys.workflowTasks(workspaceId, runId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/workflow-runs/{run_id}/tasks", {
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { run_id: runId },
          },
        }),
      ),
  });
}

export function useWorkflowApprovalQuery(workspaceId: string, runId: string, enabled: boolean) {
  const client = useApiClient();
  return useQuery<Approval>({
    enabled: Boolean(workspaceId && runId && enabled),
    queryKey: queryKeys.workflowApproval(workspaceId, runId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/workflow-runs/{run_id}/approval", {
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { run_id: runId },
          },
        }),
      ),
  });
}

export function useAgentsQuery() {
  const client = useApiClient();
  const { session } = useAuth();
  const workspaceId = session?.workspaceId ?? "";
  return useQuery<AgentCollection>({
    queryKey: queryKeys.agents(workspaceId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/agents", {
          params: { header: { "X-Workspace-ID": workspaceId } },
        }),
      ),
  });
}

const terminalAgentStatuses = new Set([
  "succeeded",
  "failed",
  "rejected",
  "budget_exhausted",
  "limit_exceeded",
]);

export function useAgentRunQuery(workspaceId: string, runId: string) {
  const client = useApiClient();
  return useQuery<AgentRun>({
    enabled: Boolean(workspaceId && runId),
    queryKey: queryKeys.agentRun(workspaceId, runId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/agent-runs/{run_id}", {
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { run_id: runId },
          },
        }),
      ),
    refetchInterval: (query) =>
      query.state.data && terminalAgentStatuses.has(query.state.data.status) ? false : 2_000,
  });
}

export function useModelStatusQuery() {
  const client = useApiClient();
  const { session } = useAuth();
  const workspaceId = session?.workspaceId ?? "";
  return useQuery<ModelStatus>({
    queryKey: queryKeys.modelStatus(workspaceId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/models/status", {
          params: { header: { "X-Workspace-ID": workspaceId } },
        }),
      ),
    refetchInterval: 30_000,
  });
}

export function useToolStatusQuery() {
  const client = useApiClient();
  const { session } = useAuth();
  const workspaceId = session?.workspaceId ?? "";
  return useQuery<ToolStatus>({
    queryKey: queryKeys.toolStatus(workspaceId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/tools/status", {
          params: { header: { "X-Workspace-ID": workspaceId } },
        }),
      ),
    refetchInterval: 30_000,
  });
}

export function useConsistencyCheckQuery(workspaceId: string, projectId: string, runId: string) {
  const client = useApiClient();
  return useQuery<ConsistencyCheck>({
    enabled: Boolean(workspaceId && projectId && runId),
    queryKey: queryKeys.consistencyCheck(workspaceId, projectId, runId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/projects/{project_id}/consistency/checks/{run_id}", {
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { project_id: projectId, run_id: runId },
          },
        }),
      ),
  });
}

export function useConsistencyResolutionQuery(
  workspaceId: string,
  projectId: string,
  proposalId: string,
) {
  const client = useApiClient();
  return useQuery<Resolution>({
    enabled: Boolean(workspaceId && projectId && proposalId),
    queryKey: queryKeys.consistencyResolution(workspaceId, projectId, proposalId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/projects/{project_id}/consistency/resolutions/{proposal_id}", {
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { project_id: projectId, proposal_id: proposalId },
          },
        }),
      ),
  });
}

export function useQualityEvaluationQuery(workspaceId: string, projectId: string, runId: string) {
  const client = useApiClient();
  return useQuery<QualityResult>({
    enabled: Boolean(workspaceId && projectId && runId),
    queryKey: queryKeys.qualityEvaluation(workspaceId, projectId, runId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/projects/{project_id}/quality/evaluations/{run_id}", {
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { project_id: projectId, run_id: runId },
          },
        }),
      ),
  });
}

export function useBehaviorConsentQuery(workspaceId: string, projectId: string) {
  const client = useApiClient();
  return useQuery<BehaviorConsentStatus>({
    enabled: Boolean(workspaceId && projectId),
    queryKey: queryKeys.behaviorConsent(workspaceId, projectId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/projects/{project_id}/feedback/behavior-consent", {
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { project_id: projectId },
          },
        }),
      ),
  });
}

export function useFeedbackQuery(workspaceId: string, projectId: string, eventId: string) {
  const client = useApiClient();
  return useQuery<Feedback>({
    enabled: Boolean(workspaceId && projectId && eventId),
    queryKey: queryKeys.feedback(workspaceId, projectId, eventId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/projects/{project_id}/feedback/{event_id}", {
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { event_id: eventId, project_id: projectId },
          },
        }),
      ),
  });
}

export function useMetricPointQuery(workspaceId: string, projectId: string, pointId: string) {
  const client = useApiClient();
  return useQuery<MetricPoint>({
    enabled: Boolean(workspaceId && projectId && pointId),
    queryKey: queryKeys.metricPoint(workspaceId, projectId, pointId),
    queryFn: async () => {
      const point = unwrapApiResult(
        await client.GET("/api/v1/projects/{project_id}/metric-points/{point_id}", {
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { point_id: pointId, project_id: projectId },
          },
        }),
      );
      return {
        ...point,
        dimensions: point.dimensions.map((dimension): [string, string] => {
          const [key, value] = dimension;
          if (key === undefined || value === undefined || dimension.length !== 2) {
            throw new Error("Metric dimension tuple does not match the generated schema");
          }
          return [key, value];
        }),
      };
    },
  });
}

export function useDiagnosticQuery(workspaceId: string, projectId: string, findingId: string) {
  const client = useApiClient();
  return useQuery<Diagnostic>({
    enabled: Boolean(workspaceId && projectId && findingId),
    queryKey: queryKeys.diagnostic(workspaceId, projectId, findingId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/projects/{project_id}/diagnostics/{finding_id}", {
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { finding_id: findingId, project_id: projectId },
          },
        }),
      ),
  });
}

export function useExperimentQuery(workspaceId: string, projectId: string, experimentId: string) {
  const client = useApiClient();
  return useQuery<Experiment>({
    enabled: Boolean(workspaceId && projectId && experimentId),
    queryKey: queryKeys.experiment(workspaceId, projectId, experimentId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/projects/{project_id}/experiments/{experiment_id}", {
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { experiment_id: experimentId, project_id: projectId },
          },
        }),
      ),
  });
}

export function useImprovementProposalQuery(
  workspaceId: string,
  projectId: string,
  proposalId: string,
) {
  const client = useApiClient();
  return useQuery<ImprovementProposal>({
    enabled: Boolean(workspaceId && projectId && proposalId),
    queryKey: queryKeys.improvementProposal(workspaceId, projectId, proposalId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/projects/{project_id}/improvement-proposals/{proposal_id}", {
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { project_id: projectId, proposal_id: proposalId },
          },
        }),
      ),
  });
}

export function useWorkspacesQuery() {
  const client = useApiClient();
  const { session } = useAuth();
  const workspaceId = session?.workspaceId ?? "";
  return useQuery<WorkspaceCollection>({
    queryKey: queryKeys.workspaces(workspaceId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/workspaces", {
          params: {
            header: { "X-Workspace-ID": workspaceId },
            query: { limit: 100 },
          },
        }),
      ),
  });
}

export function useWorkspaceQuery(workspaceId: string) {
  const client = useApiClient();
  const { session } = useAuth();
  const scopeId = session?.workspaceId ?? "";
  return useQuery<Workspace>({
    queryKey: queryKeys.workspace(workspaceId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/workspaces/{workspace_id}", {
          params: {
            header: { "X-Workspace-ID": scopeId },
            path: { workspace_id: workspaceId },
          },
        }),
      ),
  });
}

export function useProjectsQuery(workspaceId: string) {
  const client = useApiClient();
  const { session } = useAuth();
  const scopeId = session?.workspaceId ?? "";
  return useQuery<ProjectCollection>({
    enabled: Boolean(workspaceId),
    queryKey: queryKeys.projects(workspaceId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/workspaces/{workspace_id}/projects", {
          params: {
            header: { "X-Workspace-ID": scopeId },
            path: { workspace_id: workspaceId },
            query: { limit: 100, sort: "name", status: "active" },
          },
        }),
      ),
  });
}

export function useProjectQuery(workspaceId: string, projectId: string) {
  const client = useApiClient();
  const { session } = useAuth();
  const scopeId = session?.workspaceId ?? "";
  return useQuery<Project>({
    queryKey: queryKeys.project(workspaceId, projectId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/projects/{project_id}", {
          params: {
            header: { "X-Workspace-ID": scopeId },
            path: { project_id: projectId },
          },
        }),
      ),
  });
}

export function useArtifactsQuery(workspaceId: string, projectId: string) {
  const client = useApiClient();
  return useQuery<ArtifactCollection>({
    enabled: Boolean(workspaceId && projectId),
    queryKey: queryKeys.artifacts(workspaceId, projectId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/projects/{project_id}/artifacts", {
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { project_id: projectId },
            query: { limit: 100, sort: "created_at" },
          },
        }),
      ),
  });
}

export function useArtifactQuery(workspaceId: string, projectId: string, artifactId: string) {
  const client = useApiClient();
  return useQuery<Artifact>({
    enabled: Boolean(workspaceId && projectId && artifactId),
    queryKey: queryKeys.artifact(workspaceId, projectId, artifactId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/projects/{project_id}/artifacts/{artifact_id}", {
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { artifact_id: artifactId, project_id: projectId },
          },
        }),
      ),
  });
}

export function useRevisionsQuery(workspaceId: string, projectId: string, artifactId: string) {
  const client = useApiClient();
  return useQuery<RevisionCollection>({
    enabled: Boolean(workspaceId && projectId && artifactId),
    queryKey: queryKeys.revisions(workspaceId, projectId, artifactId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/projects/{project_id}/artifacts/{artifact_id}/revisions", {
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { artifact_id: artifactId, project_id: projectId },
            query: { limit: 100 },
          },
        }),
      ),
  });
}

export function useAssetsQuery(workspaceId: string, projectId: string) {
  const client = useApiClient();
  return useQuery<AssetCollection>({
    enabled: Boolean(workspaceId && projectId),
    queryKey: queryKeys.assets(workspaceId, projectId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/projects/{project_id}/assets", {
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { project_id: projectId },
            query: { limit: 100, sort: "created_at" },
          },
        }),
      ),
  });
}

const terminalIngestionStatuses = new Set(["ready", "failed"]);

export function useIngestionRunQuery(workspaceId: string, runId: string) {
  const client = useApiClient();
  return useQuery<IngestionRun>({
    enabled: Boolean(workspaceId && runId),
    queryKey: queryKeys.ingestionRun(workspaceId, runId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/knowledge/ingestion-runs/{run_id}", {
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { run_id: runId },
          },
        }),
      ),
    refetchInterval: (query) =>
      query.state.data && terminalIngestionStatuses.has(query.state.data.status) ? false : 2_000,
  });
}

export function useMemoryQuery(workspaceId: string, projectId: string, memoryId: string) {
  const client = useApiClient();
  return useQuery<Memory>({
    enabled: Boolean(workspaceId && projectId && memoryId),
    queryKey: queryKeys.memory(workspaceId, projectId, memoryId),
    queryFn: async () =>
      unwrapApiResult(
        await client.GET("/api/v1/projects/{project_id}/memories/{memory_id}", {
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { memory_id: memoryId, project_id: projectId },
          },
        }),
      ),
  });
}
