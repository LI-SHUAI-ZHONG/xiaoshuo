"use client";

import { Badge, Button, Dialog, EmptyState, Input, Select } from "@accos/ui";
import { useState, type SyntheticEvent } from "react";

import { InlineApiError } from "../../components/inline-api-error";
import { StateResolver } from "../../components/state-resolver";
import {
  useDecideImprovementProposalMutation,
  useGrantBehaviorConsentMutation,
  useWithdrawBehaviorConsentMutation,
} from "../../lib/api/mutations";
import {
  useBehaviorConsentQuery,
  useDiagnosticQuery,
  useExperimentQuery,
  useFeedbackQuery,
  useImprovementProposalQuery,
  useMetricPointQuery,
  useProjectsQuery,
} from "../../lib/api/queries";
import { useIdentity } from "../../providers/identity-provider";
import { StatusBadge } from "../monitoring/status-badge";
import { canDecideApprovals, canOperateProject } from "../monitoring/status";

type PendingDecision = "approve" | "reject" | "withdraw" | null;

interface LookupProps {
  label: string;
  onSubmit: (event: SyntheticEvent<HTMLFormElement>) => void;
  setValue: (value: string) => void;
  value: string;
}

function LookupForm({ label, onSubmit, setValue, value }: LookupProps) {
  return (
    <form className="studio-form-row" onSubmit={onSubmit}>
      <Input
        label={label}
        onChange={(event) => {
          setValue(event.target.value);
        }}
        required
        value={value}
      />
      <Button type="submit" variant="secondary">
        读取
      </Button>
    </form>
  );
}

export function FeedbackWorkspace() {
  const identity = useIdentity();
  const projects = useProjectsQuery(identity.workspace_id);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [policyVersion, setPolicyVersion] = useState("behavior-consent-v1");
  const [pendingDecision, setPendingDecision] = useState<PendingDecision>(null);
  const [feedbackInput, setFeedbackInput] = useState("");
  const [feedbackId, setFeedbackId] = useState("");
  const [metricInput, setMetricInput] = useState("");
  const [metricId, setMetricId] = useState("");
  const [diagnosticInput, setDiagnosticInput] = useState("");
  const [diagnosticId, setDiagnosticId] = useState("");
  const [experimentInput, setExperimentInput] = useState("");
  const [experimentId, setExperimentId] = useState("");
  const [proposalInput, setProposalInput] = useState("");
  const [proposalId, setProposalId] = useState("");

  const projectId =
    selectedProjectId.length > 0 ? selectedProjectId : (projects.data?.items[0]?.id ?? "");
  const selectedProject = projects.data?.items.find((project) => project.id === projectId);
  const consent = useBehaviorConsentQuery(identity.workspace_id, projectId);
  const grantConsent = useGrantBehaviorConsentMutation(identity.workspace_id, projectId);
  const withdrawConsent = useWithdrawBehaviorConsentMutation(identity.workspace_id, projectId);
  const feedback = useFeedbackQuery(identity.workspace_id, projectId, feedbackId);
  const metric = useMetricPointQuery(identity.workspace_id, projectId, metricId);
  const diagnostic = useDiagnosticQuery(identity.workspace_id, projectId, diagnosticId);
  const experiment = useExperimentQuery(identity.workspace_id, projectId, experimentId);
  const proposal = useImprovementProposalQuery(identity.workspace_id, projectId, proposalId);
  const decideProposal = useDecideImprovementProposalMutation(identity.workspace_id, projectId);

  if (projects.isPending) return <StateResolver state="loading" />;
  if (projects.isError)
    return <StateResolver error={projects.error} onRetry={() => void projects.refetch()} />;
  if (projects.data.items.length === 0) {
    return (
      <section className="studio-page">
        <header className="studio-page__header">
          <p className="studio-eyebrow">Feedback</p>
          <h1>反馈与受控改进</h1>
        </header>
        <EmptyState
          description="Feedback API 以 Project 为隔离边界；当前 Workspace 没有可访问 Project。"
          title="暂无 Project"
        />
      </section>
    );
  }

  const canWrite = selectedProject ? canOperateProject(identity, selectedProject.status) : false;
  const canDecide =
    canDecideApprovals(identity) && proposal.data?.requested_by !== identity.actor_id;

  function clearLookups() {
    setFeedbackId("");
    setMetricId("");
    setDiagnosticId("");
    setExperimentId("");
    setProposalId("");
  }

  async function confirmDecision() {
    if (pendingDecision === "withdraw") {
      await withdrawConsent.mutateAsync();
    } else if (pendingDecision && proposal.data) {
      await decideProposal.mutateAsync({
        decision: pendingDecision,
        proposalId: proposal.data.id,
        version: proposal.data.version,
      });
    }
    setPendingDecision(null);
  }

  return (
    <section className="studio-page studio-page--wide">
      <header className="studio-page__header studio-page__header--split">
        <div>
          <p className="studio-eyebrow">Feedback / Evolution</p>
          <h1>反馈、指标与受控改进</h1>
          <p>只投影真实 Project 数据；没有集合 API 的资源通过已知 ID 恢复读取。</p>
        </div>
        <Badge tone={canWrite ? "success" : "warning"}>{canWrite ? "可写" : "只读"}</Badge>
      </header>

      <section className="studio-panel studio-panel--compact">
        <Select
          description="切换会重新绑定所有 Project-scoped API。"
          label="Project"
          onChange={(event) => {
            setSelectedProjectId(event.target.value);
            clearLookups();
          }}
          value={projectId}
        >
          {projects.data.items.map((project) => (
            <option key={project.id} value={project.id}>
              {project.name} · {project.id}
            </option>
          ))}
        </Select>
      </section>

      <section className="studio-panel">
        <div className="studio-panel__heading">
          <div>
            <p className="studio-eyebrow">Behavior consent</p>
            <h2>行为数据同意</h2>
          </div>
          {consent.data ? (
            <StatusBadge status={consent.data.active ? "active" : "withdrawn"} />
          ) : null}
        </div>
        {consent.isPending ? <p className="studio-muted">正在读取同意状态…</p> : null}
        {consent.isError ? <InlineApiError error={consent.error} title="行为同意读取失败" /> : null}
        {consent.data ? (
          <dl className="studio-definition-list">
            <div>
              <dt>当前状态</dt>
              <dd>{consent.data.active ? "已同意" : "未同意或已撤回"}</dd>
            </div>
            <div>
              <dt>策略版本</dt>
              <dd>{consent.data.consent?.policy_version ?? "无"}</dd>
            </div>
            <div>
              <dt>授权时间</dt>
              <dd>{consent.data.consent?.granted_at ?? "无"}</dd>
            </div>
            <div>
              <dt>撤回时间</dt>
              <dd>{consent.data.consent?.withdrawn_at ?? "无"}</dd>
            </div>
          </dl>
        ) : null}
        {canWrite && consent.data && !consent.data.active ? (
          <form
            className="studio-form-row"
            onSubmit={(event) => {
              event.preventDefault();
              void grantConsent.mutateAsync({ policyVersion: policyVersion.trim() });
            }}
          >
            <Input
              label="同意策略版本"
              onChange={(event) => {
                setPolicyVersion(event.target.value);
              }}
              pattern="[a-z][a-z0-9_.-]*"
              required
              value={policyVersion}
            />
            <Button busy={grantConsent.isPending} type="submit">
              明确同意
            </Button>
          </form>
        ) : null}
        {canWrite && consent.data?.active ? (
          <Button
            onClick={() => {
              setPendingDecision("withdraw");
            }}
            variant="danger"
          >
            撤回行为同意
          </Button>
        ) : null}
        {grantConsent.isError ? (
          <InlineApiError error={grantConsent.error} title="同意写入失败" />
        ) : null}
        {withdrawConsent.isError ? (
          <InlineApiError error={withdrawConsent.error} title="同意撤回失败" />
        ) : null}
        {withdrawConsent.data ? (
          <p className="studio-success-text">
            已撤回；服务端写入 {withdrawConsent.data.tombstone_count} 个 tombstone，并匿名化
            {withdrawConsent.data.anonymized_event_ids.length} 个事件。
          </p>
        ) : null}
      </section>

      <section className="studio-two-column">
        <article className="studio-panel">
          <div>
            <p className="studio-eyebrow">Feedback event</p>
            <h2>反馈事件</h2>
          </div>
          <LookupForm
            label="Feedback Event ID"
            onSubmit={(event) => {
              event.preventDefault();
              setFeedbackId(feedbackInput.trim());
            }}
            setValue={setFeedbackInput}
            value={feedbackInput}
          />
          {feedback.isPending && feedbackId ? <p className="studio-muted">正在读取…</p> : null}
          {feedback.isError ? (
            <InlineApiError error={feedback.error} title="Feedback 读取失败" />
          ) : null}
          {feedback.data ? (
            <dl className="studio-definition-list studio-definition-list--compact">
              <div>
                <dt>来源 / 信号</dt>
                <dd>
                  {feedback.data.source} / {feedback.data.signal_code}
                </dd>
              </div>
              <div>
                <dt>数值</dt>
                <dd>{feedback.data.numeric_value ?? "无"}</dd>
              </div>
              <div>
                <dt>Actor</dt>
                <dd>{feedback.data.actor_id ?? "已脱敏"}</dd>
              </div>
              <div>
                <dt>状态</dt>
                <dd>
                  <StatusBadge status={feedback.data.status} />
                </dd>
              </div>
            </dl>
          ) : null}
        </article>

        <article className="studio-panel">
          <div>
            <p className="studio-eyebrow">Sanitized metric</p>
            <h2>脱敏指标点</h2>
          </div>
          <LookupForm
            label="Metric Point ID"
            onSubmit={(event) => {
              event.preventDefault();
              setMetricId(metricInput.trim());
            }}
            setValue={setMetricInput}
            value={metricInput}
          />
          {metric.isPending && metricId ? <p className="studio-muted">正在读取…</p> : null}
          {metric.isError ? <InlineApiError error={metric.error} title="指标读取失败" /> : null}
          {metric.data ? (
            <dl className="studio-definition-list studio-definition-list--compact">
              <div>
                <dt>指标</dt>
                <dd>{metric.data.metric_name}</dd>
              </div>
              <div>
                <dt>值</dt>
                <dd>{metric.data.value}</dd>
              </div>
              <div>
                <dt>维度</dt>
                <dd>
                  {metric.data.dimensions.map(([key, value]) => `${key}=${value}`).join(", ") ||
                    "无"}
                </dd>
              </div>
              <div>
                <dt>聚合资格</dt>
                <dd>{metric.data.included ? "已纳入" : "未纳入 / tombstoned"}</dd>
              </div>
            </dl>
          ) : null}
        </article>

        <article className="studio-panel">
          <div>
            <p className="studio-eyebrow">Diagnostic finding</p>
            <h2>诊断 Finding</h2>
          </div>
          <LookupForm
            label="Diagnostic Finding ID"
            onSubmit={(event) => {
              event.preventDefault();
              setDiagnosticId(diagnosticInput.trim());
            }}
            setValue={setDiagnosticInput}
            value={diagnosticInput}
          />
          {diagnostic.isPending && diagnosticId ? <p className="studio-muted">正在读取…</p> : null}
          {diagnostic.isError ? (
            <InlineApiError error={diagnostic.error} title="Diagnostic 读取失败" />
          ) : null}
          {diagnostic.data ? (
            <dl className="studio-definition-list studio-definition-list--compact">
              <div>
                <dt>Finding</dt>
                <dd>{diagnostic.data.finding_code}</dd>
              </div>
              <div>
                <dt>严重度</dt>
                <dd>
                  <StatusBadge status={diagnostic.data.severity} />
                </dd>
              </div>
              <div>
                <dt>观测 / 阈值</dt>
                <dd>
                  {diagnostic.data.observed_value} / {diagnostic.data.threshold_value}
                </dd>
              </div>
              <div>
                <dt>规则</dt>
                <dd>
                  {diagnostic.data.rule_key} / {diagnostic.data.rule_version}
                </dd>
              </div>
            </dl>
          ) : null}
        </article>

        <article className="studio-panel">
          <div>
            <p className="studio-eyebrow">Experiment</p>
            <h2>受控实验</h2>
          </div>
          <LookupForm
            label="Experiment ID"
            onSubmit={(event) => {
              event.preventDefault();
              setExperimentId(experimentInput.trim());
            }}
            setValue={setExperimentInput}
            value={experimentInput}
          />
          {experiment.isPending && experimentId ? <p className="studio-muted">正在读取…</p> : null}
          {experiment.isError ? (
            <InlineApiError error={experiment.error} title="Experiment 读取失败" />
          ) : null}
          {experiment.data ? (
            <>
              <div className="studio-panel__heading">
                <strong>{experiment.data.experiment_key}</strong>
                <StatusBadge status={experiment.data.status} />
              </div>
              <ul className="studio-compact-list">
                {experiment.data.variants.map((variant) => (
                  <li key={variant.id}>
                    {variant.variant_key}: {variant.configuration_reference}
                  </li>
                ))}
              </ul>
              <p className="studio-code-line">结果：{experiment.data.result_code ?? "尚未完成"}</p>
            </>
          ) : null}
        </article>
      </section>

      <section className="studio-panel">
        <div>
          <p className="studio-eyebrow">Improvement proposal</p>
          <h2>改进提案与人工批准</h2>
        </div>
        <LookupForm
          label="Improvement Proposal ID"
          onSubmit={(event) => {
            event.preventDefault();
            setProposalId(proposalInput.trim());
          }}
          setValue={setProposalInput}
          value={proposalInput}
        />
        {proposal.isPending && proposalId ? <p className="studio-muted">正在读取…</p> : null}
        {proposal.isError ? (
          <InlineApiError error={proposal.error} title="Improvement Proposal 读取失败" />
        ) : null}
        {proposal.data ? (
          <>
            <div className="studio-panel__heading">
              <span className="studio-code-value">{proposal.data.id}</span>
              <StatusBadge status={proposal.data.state} />
            </div>
            <dl className="studio-definition-list">
              <div>
                <dt>建议动作</dt>
                <dd>{proposal.data.action ?? "尚未规划"}</dd>
              </div>
              <div>
                <dt>诊断来源</dt>
                <dd className="studio-code-value">
                  {proposal.data.diagnostic_finding_ids.join(", ")}
                </dd>
              </div>
              <div>
                <dt>模拟证据</dt>
                <dd>{proposal.data.simulation_evidence.join(", ") || "尚无"}</dd>
              </div>
              <div>
                <dt>部署状态</dt>
                <dd>
                  {proposal.data.state === "externally_deployed"
                    ? "由外部系统证明已部署"
                    : "未部署"}
                </dd>
              </div>
            </dl>
            {proposal.data.state === "awaiting_approval" && canDecide ? (
              <div className="studio-action-row">
                <Button
                  onClick={() => {
                    setPendingDecision("approve");
                  }}
                >
                  批准提案
                </Button>
                <Button
                  onClick={() => {
                    setPendingDecision("reject");
                  }}
                  variant="danger"
                >
                  拒绝提案
                </Button>
              </div>
            ) : null}
            {proposal.data.state === "awaiting_approval" && !canDecide ? (
              <p className="studio-readonly-note">
                当前身份无 approval:decide，或是提案发起人；服务端强制职责分离。
              </p>
            ) : null}
          </>
        ) : null}
        {decideProposal.isError ? (
          <InlineApiError error={decideProposal.error} title="Improvement 决定失败" />
        ) : null}
      </section>

      <Dialog
        description={
          pendingDecision === "withdraw"
            ? "撤回会由服务端匿名化已同意的行为事件并写入 tombstone。"
            : "批准只改变受控提案状态；本系统不会自行改代码或部署。"
        }
        footer={
          <div className="studio-action-row">
            <Button
              onClick={() => {
                setPendingDecision(null);
              }}
              variant="secondary"
            >
              返回
            </Button>
            <Button
              busy={withdrawConsent.isPending || decideProposal.isPending}
              onClick={() => void confirmDecision()}
              variant={pendingDecision === "approve" ? "primary" : "danger"}
            >
              确认
            </Button>
          </div>
        }
        onOpenChange={(open) => {
          if (!open && !withdrawConsent.isPending && !decideProposal.isPending) {
            setPendingDecision(null);
          }
        }}
        open={pendingDecision !== null}
        title={
          pendingDecision === "withdraw"
            ? "确认撤回行为同意"
            : pendingDecision === "approve"
              ? "确认批准改进提案"
              : "确认拒绝改进提案"
        }
      >
        <p>403、409、429 和终态竞争均以服务端响应为准。</p>
      </Dialog>
    </section>
  );
}
