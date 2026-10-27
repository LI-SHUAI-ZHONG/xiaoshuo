"use client";

import type { components } from "@accos/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { unwrapApiResult } from "./queries";
import { queryKeys } from "./query-keys";
import { useApiClient } from "../../providers/api-provider";

type ArtifactCreate = components["schemas"]["ArtifactCreateRequest"];
type Artifact = components["schemas"]["ArtifactResponse"];
type AgentRunCreate = components["schemas"]["AgentRunCreateRequest"];
type ApprovalDecision = components["schemas"]["ApprovalDecisionRequest"];
type AsyncRunReference = components["schemas"]["AsyncRunReference"];
type AssetUpload = components["schemas"]["AssetUploadRequest"];
type Asset = components["schemas"]["AssetResponse"];
type BehaviorConsent = components["schemas"]["BehaviorConsentResponse"];
type BehaviorConsentStatus = components["schemas"]["BehaviorConsentStatusResponse"];
type BehaviorConsentWithdrawal = components["schemas"]["BehaviorConsentWithdrawalResponse"];
type ConsistencyCheck = components["schemas"]["ConsistencyCheckResponse"];
type ConsistencyCheckRequest = components["schemas"]["ConsistencyCheckRequest"];
type Resolution = components["schemas"]["ResolutionResponse"];
type ResolutionCreate = components["schemas"]["ResolutionCreateRequest"];
type IngestionAccepted = components["schemas"]["IngestionAcceptedResponse"];
type ImprovementProposal = components["schemas"]["ImprovementProposalResponse"];
type KnowledgeSearch = components["schemas"]["KnowledgeSearchRequest"];
type KnowledgeSearchResult = components["schemas"]["KnowledgeSearchResponse"];
type MemoryWrite = components["schemas"]["MemoryWriteRequest"];
type Memory = components["schemas"]["MemoryResponse"];
type Project = components["schemas"]["ProjectResponse"];
type QualityResult = components["schemas"]["QualityResultResponse"];
type Rubric = components["schemas"]["RubricResponse"];
type EvaluationRun = components["schemas"]["EvaluationRunResponse"];
type Revision = components["schemas"]["RevisionResponse"];
type WorkflowRun = components["schemas"]["WorkflowRunResponse"];

function idempotencyKey(prefix: string): string {
  return `${prefix}-${globalThis.crypto.randomUUID()}`;
}

export function useCreateProjectMutation(workspaceId: string) {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation<Project, unknown, { name: string }>({
    mutationFn: async ({ name }) =>
      unwrapApiResult(
        await client.POST("/api/v1/workspaces/{workspace_id}/projects", {
          body: { name },
          params: {
            header: {
              "Idempotency-Key": idempotencyKey("studio-project"),
              "X-Workspace-ID": workspaceId,
            },
            path: { workspace_id: workspaceId },
          },
        }),
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.projects(workspaceId) });
    },
  });
}

export function useCreateArtifactMutation(workspaceId: string, projectId: string) {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation<Artifact, unknown, ArtifactCreate>({
    mutationFn: async (body) =>
      unwrapApiResult(
        await client.POST("/api/v1/projects/{project_id}/artifacts", {
          body,
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { project_id: projectId },
          },
        }),
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.artifacts(workspaceId, projectId),
      });
    },
  });
}

export function useCreateRevisionMutation(workspaceId: string, projectId: string) {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation<
    Revision,
    unknown,
    { artifactId: string; contentHash: string; contentReference: string; version: number }
  >({
    mutationFn: async ({ artifactId, contentHash, contentReference, version }) =>
      unwrapApiResult(
        await client.POST("/api/v1/projects/{project_id}/artifacts/{artifact_id}/revisions", {
          body: { content_hash: contentHash, content_reference: contentReference },
          params: {
            header: {
              "If-Match": `"${version.toString()}"`,
              "X-Workspace-ID": workspaceId,
            },
            path: { artifact_id: artifactId, project_id: projectId },
          },
        }),
      ),
    onSuccess: async (_revision, variables) => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: queryKeys.artifact(workspaceId, projectId, variables.artifactId),
        }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.artifacts(workspaceId, projectId),
        }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.revisions(workspaceId, projectId, variables.artifactId),
        }),
      ]);
    },
  });
}

export function useUploadAssetMutation(workspaceId: string, projectId: string) {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation<Asset, unknown, AssetUpload>({
    mutationFn: async (body) =>
      unwrapApiResult(
        await client.POST("/api/v1/projects/{project_id}/assets", {
          body,
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { project_id: projectId },
          },
        }),
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.assets(workspaceId, projectId) });
    },
  });
}

export function useCreateIngestionMutation(workspaceId: string, projectId: string) {
  const client = useApiClient();
  return useMutation<IngestionAccepted, unknown, { assetId: string }>({
    mutationFn: async ({ assetId }) =>
      unwrapApiResult(
        await client.POST("/api/v1/projects/{project_id}/knowledge/ingestion-runs", {
          body: { asset_id: assetId, verification_policy: "not_required" },
          params: {
            header: {
              "Idempotency-Key": idempotencyKey("studio-ingestion"),
              "X-Workspace-ID": workspaceId,
            },
            path: { project_id: projectId },
          },
        }),
      ),
  });
}

export function useKnowledgeSearchMutation(workspaceId: string, projectId: string) {
  const client = useApiClient();
  return useMutation<KnowledgeSearchResult, unknown, KnowledgeSearch>({
    mutationFn: async (body) =>
      unwrapApiResult(
        await client.POST("/api/v1/projects/{project_id}/knowledge/search", {
          body,
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { project_id: projectId },
          },
        }),
      ),
  });
}

export function useCreateMemoryMutation(workspaceId: string, projectId: string) {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation<Memory, unknown, MemoryWrite>({
    mutationFn: async (body) =>
      unwrapApiResult(
        await client.POST("/api/v1/projects/{project_id}/memories", {
          body,
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { project_id: projectId },
          },
        }),
      ),
    onSuccess: (memory) => {
      queryClient.setQueryData(queryKeys.memory(workspaceId, projectId, memory.id), memory);
    },
  });
}

export function useCreateWorkflowRunMutation(workspaceId: string, projectId: string) {
  const client = useApiClient();
  return useMutation<AsyncRunReference, unknown, { inputReference: string; workflowName: string }>({
    mutationFn: async ({ inputReference, workflowName }) =>
      unwrapApiResult(
        await client.POST("/api/v1/projects/{project_id}/workflows/{workflow_name}/runs", {
          body: { input_reference: inputReference },
          params: {
            header: {
              "Idempotency-Key": idempotencyKey("studio-workflow"),
              "X-Workspace-ID": workspaceId,
            },
            path: { project_id: projectId, workflow_name: workflowName },
          },
        }),
      ),
  });
}

export type WorkflowControlAction = "cancel" | "pause" | "resume";

export function useWorkflowControlMutation(workspaceId: string, runId: string) {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation<WorkflowRun, unknown, WorkflowControlAction>({
    mutationFn: async (action) => {
      const options = {
        params: {
          header: { "X-Workspace-ID": workspaceId },
          path: { run_id: runId },
        },
      } as const;
      if (action === "pause") {
        return unwrapApiResult(await client.POST("/api/v1/workflow-runs/{run_id}/pause", options));
      }
      if (action === "resume") {
        return unwrapApiResult(await client.POST("/api/v1/workflow-runs/{run_id}/resume", options));
      }
      return unwrapApiResult(await client.POST("/api/v1/workflow-runs/{run_id}/cancel", options));
    },
    onSuccess: (run) => {
      queryClient.setQueryData(queryKeys.workflowRun(workspaceId, runId), run);
    },
  });
}

export function useWorkflowApprovalDecisionMutation(workspaceId: string, runId: string) {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation<WorkflowRun, unknown, ApprovalDecision>({
    mutationFn: async (body) =>
      unwrapApiResult(
        await client.POST("/api/v1/workflow-runs/{run_id}/approval/decision", {
          body,
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { run_id: runId },
          },
        }),
      ),
    onSuccess: async (run) => {
      queryClient.setQueryData(queryKeys.workflowRun(workspaceId, runId), run);
      await queryClient.invalidateQueries({
        queryKey: queryKeys.workflowApproval(workspaceId, runId),
      });
    },
  });
}

export function useCreateDirectorRunMutation(workspaceId: string, projectId: string) {
  const client = useApiClient();
  return useMutation<AsyncRunReference, unknown, AgentRunCreate>({
    mutationFn: async (body) =>
      unwrapApiResult(
        await client.POST("/api/v1/projects/{project_id}/agents/director/runs", {
          body,
          params: {
            header: {
              "Idempotency-Key": idempotencyKey("studio-agent"),
              "X-Workspace-ID": workspaceId,
            },
            path: { project_id: projectId },
          },
        }),
      ),
  });
}

export function useCreateConsistencyCheckMutation(workspaceId: string, projectId: string) {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation<ConsistencyCheck, unknown, ConsistencyCheckRequest>({
    mutationFn: async (body) =>
      unwrapApiResult(
        await client.POST("/api/v1/projects/{project_id}/consistency/checks", {
          body,
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { project_id: projectId },
          },
        }),
      ),
    onSuccess: (check) => {
      queryClient.setQueryData(queryKeys.consistencyCheck(workspaceId, projectId, check.id), check);
    },
  });
}

export function useCreateConsistencyResolutionMutation(workspaceId: string, projectId: string) {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation<Resolution, unknown, ResolutionCreate>({
    mutationFn: async (body) =>
      unwrapApiResult(
        await client.POST("/api/v1/projects/{project_id}/consistency/resolutions", {
          body,
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { project_id: projectId },
          },
        }),
      ),
    onSuccess: (proposal) => {
      queryClient.setQueryData(
        queryKeys.consistencyResolution(workspaceId, projectId, proposal.id),
        proposal,
      );
    },
  });
}

export function useDecideConsistencyResolutionMutation(workspaceId: string, projectId: string) {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation<
    Resolution,
    unknown,
    { decision: "approve" | "reject"; proposalId: string; version: number }
  >({
    mutationFn: async ({ decision, proposalId, version }) =>
      unwrapApiResult(
        await client.POST(
          "/api/v1/projects/{project_id}/consistency/resolutions/{proposal_id}/decision",
          {
            body: { decision },
            params: {
              header: {
                "If-Match": `"${version.toString()}"`,
                "X-Workspace-ID": workspaceId,
              },
              path: { project_id: projectId, proposal_id: proposalId },
            },
          },
        ),
      ),
    onSuccess: (proposal) => {
      queryClient.setQueryData(
        queryKeys.consistencyResolution(workspaceId, projectId, proposal.id),
        proposal,
      );
    },
  });
}

export interface QualityFlowInput {
  consistencyStatus: string;
  dimensionKey: string;
  inputReference: string;
  rubricKey: string;
}

export interface QualityFlowResult {
  evaluation: EvaluationRun;
  result: QualityResult;
  rubric: Rubric;
}

export function useRunQualityFlowMutation(workspaceId: string, projectId: string) {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation<QualityFlowResult, unknown, QualityFlowInput>({
    mutationFn: async ({ consistencyStatus, dimensionKey, inputReference, rubricKey }) => {
      const rubric = unwrapApiResult(
        await client.POST("/api/v1/projects/{project_id}/quality/rubrics", {
          body: {
            dimension_keys: [dimensionKey],
            rubric_key: rubricKey,
            schema_version: "quality.v1",
            version: 1,
          },
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { project_id: projectId },
          },
        }),
      );
      const evaluation = unwrapApiResult(
        await client.POST("/api/v1/projects/{project_id}/quality/evaluations", {
          body: { input_reference: inputReference, rubric_id: rubric.id },
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { project_id: projectId },
          },
        }),
      );
      const result = unwrapApiResult(
        await client.POST("/api/v1/projects/{project_id}/quality/evaluations/{run_id}/execute", {
          body: { consistency_status: consistencyStatus, input_reference: inputReference },
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { project_id: projectId, run_id: evaluation.id },
          },
        }),
      );
      return { evaluation, result, rubric };
    },
    onSuccess: ({ evaluation, result }) => {
      queryClient.setQueryData(
        queryKeys.qualityEvaluation(workspaceId, projectId, evaluation.id),
        result,
      );
    },
  });
}

export function useGrantBehaviorConsentMutation(workspaceId: string, projectId: string) {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation<BehaviorConsent, unknown, { policyVersion: string }>({
    mutationFn: async ({ policyVersion }) =>
      unwrapApiResult(
        await client.POST("/api/v1/projects/{project_id}/feedback/behavior-consent", {
          body: { policy_version: policyVersion },
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { project_id: projectId },
          },
        }),
      ),
    onSuccess: (consent) => {
      queryClient.setQueryData<BehaviorConsentStatus>(
        queryKeys.behaviorConsent(workspaceId, projectId),
        { active: true, consent },
      );
    },
  });
}

export function useWithdrawBehaviorConsentMutation(workspaceId: string, projectId: string) {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation<BehaviorConsentWithdrawal>({
    mutationFn: async () =>
      unwrapApiResult(
        await client.DELETE("/api/v1/projects/{project_id}/feedback/behavior-consent", {
          params: {
            header: { "X-Workspace-ID": workspaceId },
            path: { project_id: projectId },
          },
        }),
      ),
    onSuccess: (withdrawal) => {
      queryClient.setQueryData<BehaviorConsentStatus>(
        queryKeys.behaviorConsent(workspaceId, projectId),
        { active: false, consent: withdrawal.consent },
      );
    },
  });
}

export function useDecideImprovementProposalMutation(workspaceId: string, projectId: string) {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation<
    ImprovementProposal,
    unknown,
    { decision: "approve" | "reject"; proposalId: string; version: number }
  >({
    mutationFn: async ({ decision, proposalId, version }) =>
      unwrapApiResult(
        await client.POST(
          "/api/v1/projects/{project_id}/improvement-proposals/{proposal_id}/decision",
          {
            body: { decision },
            params: {
              header: {
                "If-Match": `"${version.toString()}"`,
                "X-Workspace-ID": workspaceId,
              },
              path: { project_id: projectId, proposal_id: proposalId },
            },
          },
        ),
      ),
    onSuccess: (proposal) => {
      queryClient.setQueryData(
        queryKeys.improvementProposal(workspaceId, projectId, proposal.id),
        proposal,
      );
    },
  });
}
