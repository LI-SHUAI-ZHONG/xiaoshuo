"use client";

import { Badge, Button, Dialog, EmptyState, Input, Select } from "@accos/ui";
import { useState, type SyntheticEvent } from "react";

import { InlineApiError } from "../../components/inline-api-error";
import {
  useCreateConsistencyCheckMutation,
  useCreateConsistencyResolutionMutation,
  useDecideConsistencyResolutionMutation,
  useRunQualityFlowMutation,
} from "../../lib/api/mutations";
import {
  useConsistencyCheckQuery,
  useConsistencyResolutionQuery,
  useQualityEvaluationQuery,
} from "../../lib/api/queries";
import { useIdentity } from "../../providers/identity-provider";
import { useProject } from "../../providers/scope-providers";
import { StatusBadge } from "../monitoring/status-badge";
import { canDecideApprovals, canOperateProject } from "../monitoring/status";
import { ProjectHeader } from "../projects/project-header";

type ResolutionDecision = "approve" | "reject";

export function QualityWorkspace() {
  const identity = useIdentity();
  const project = useProject();
  const [fieldCode, setFieldCode] = useState("");
  const [evidenceReference, setEvidenceReference] = useState("");
  const [fieldPresent, setFieldPresent] = useState("true");
  const [checkLookup, setCheckLookup] = useState("");
  const [checkId, setCheckId] = useState("");
  const [selectedFindingId, setSelectedFindingId] = useState("");
  const [strategyCode, setStrategyCode] = useState("");
  const [targetReference, setTargetReference] = useState("");
  const [targetVersion, setTargetVersion] = useState("1");
  const [resolutionLookup, setResolutionLookup] = useState("");
  const [resolutionId, setResolutionId] = useState("");
  const [pendingDecision, setPendingDecision] = useState<ResolutionDecision | null>(null);
  const [rubricKey, setRubricKey] = useState("");
  const [dimensionKey, setDimensionKey] = useState("");
  const [qualityReference, setQualityReference] = useState("");
  const [qualityRunLookup, setQualityRunLookup] = useState("");
  const [qualityRunId, setQualityRunId] = useState("");

  const createCheck = useCreateConsistencyCheckMutation(identity.workspace_id, project.id);
  const check = useConsistencyCheckQuery(identity.workspace_id, project.id, checkId);
  const createResolution = useCreateConsistencyResolutionMutation(
    identity.workspace_id,
    project.id,
  );
  const resolution = useConsistencyResolutionQuery(identity.workspace_id, project.id, resolutionId);
  const decideResolution = useDecideConsistencyResolutionMutation(
    identity.workspace_id,
    project.id,
  );
  const runQuality = useRunQualityFlowMutation(identity.workspace_id, project.id);
  const quality = useQualityEvaluationQuery(identity.workspace_id, project.id, qualityRunId);
  const canWrite = canOperateProject(identity, project.status);
  const canDecide = canDecideApprovals(identity);

  async function submitCheck(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    const result = await createCheck.mutateAsync({
      canon_changes: [],
      references: [],
      required_fields: [
        {
          evidence_reference: evidenceReference.trim(),
          field_code: fieldCode.trim(),
          present: fieldPresent === "true",
        },
      ],
      versions: [],
      workflow_run_id: null,
    });
    setCheckId(result.id);
    setSelectedFindingId(result.findings[0]?.id ?? "");
  }

  function lookupCheck(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setSelectedFindingId("");
    setCheckId(checkLookup.trim());
  }

  async function submitResolution(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFindingId) return;
    const result = await createResolution.mutateAsync({
      finding_ids: [selectedFindingId],
      impact_references: [],
      strategy_code: strategyCode.trim(),
      target_expected_version: Number(targetVersion),
      target_reference: targetReference.trim(),
      workflow_run_id: null,
    });
    setResolutionId(result.id);
  }

  function lookupResolution(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setResolutionId(resolutionLookup.trim());
  }

  async function confirmDecision() {
    if (!pendingDecision || !resolution.data) return;
    await decideResolution.mutateAsync({
      decision: pendingDecision,
      proposalId: resolution.data.id,
      version: resolution.data.version,
    });
    setPendingDecision(null);
  }

  async function submitQuality(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    const result = await runQuality.mutateAsync({
      consistencyStatus: check.data?.status ?? "not_run",
      dimensionKey: dimensionKey.trim(),
      inputReference: qualityReference.trim(),
      rubricKey: rubricKey.trim(),
    });
    setQualityRunId(result.evaluation.id);
  }

  function lookupQuality(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setQualityRunId(qualityRunLookup.trim());
  }

  return (
    <section className="studio-page studio-page--wide">
      <ProjectHeader active="quality" eyebrow="Consistency / Quality" title="一致性与质量" />

      <p className="studio-readonly-note">
        检查只读取显式断言并返回 Finding；Resolution Proposal
        必须逐项人工决定，本页不提供“自动修改全部”。
      </p>

      <section className="studio-two-column">
        <article className="studio-panel">
          <div>
            <p className="studio-eyebrow">Deterministic check</p>
            <h2>提交结构断言</h2>
          </div>
          {canWrite ? (
            <form className="studio-form-stack" onSubmit={(event) => void submitCheck(event)}>
              <Input
                description="只填写稳定字段代码，不提交创作内容。"
                label="字段代码"
                onChange={(event) => {
                  setFieldCode(event.target.value);
                }}
                pattern="[a-z][a-z0-9_.-]*"
                required
                value={fieldCode}
              />
              <Input
                label="证据引用"
                onChange={(event) => {
                  setEvidenceReference(event.target.value);
                }}
                placeholder="scheme://technical-reference"
                required
                value={evidenceReference}
              />
              <Select
                label="字段存在"
                onChange={(event) => {
                  setFieldPresent(event.target.value);
                }}
                value={fieldPresent}
              >
                <option value="true">是</option>
                <option value="false">否（产生 Finding）</option>
              </Select>
              <Button busy={createCheck.isPending} type="submit">
                运行一致性检查
              </Button>
            </form>
          ) : (
            <p className="studio-readonly-note">当前身份只能读取检查与 Finding。</p>
          )}
          {createCheck.isError ? (
            <InlineApiError error={createCheck.error} title="一致性检查失败" />
          ) : null}
        </article>

        <article className="studio-panel">
          <div>
            <p className="studio-eyebrow">Recover</p>
            <h2>按 Check ID 读取</h2>
          </div>
          <form className="studio-form-row" onSubmit={lookupCheck}>
            <Input
              label="Consistency Check ID"
              onChange={(event) => {
                setCheckLookup(event.target.value);
              }}
              required
              value={checkLookup}
            />
            <Button type="submit" variant="secondary">
              读取
            </Button>
          </form>
        </article>
      </section>

      {checkId ? (
        <section className="studio-panel">
          <div className="studio-panel__heading">
            <div>
              <p className="studio-eyebrow">Check projection</p>
              <h2>Finding 与证据</h2>
            </div>
            {check.data ? <StatusBadge status={check.data.status} /> : null}
          </div>
          {check.isPending ? <p className="studio-muted">正在读取检查…</p> : null}
          {check.isError ? <InlineApiError error={check.error} title="检查读取失败" /> : null}
          {check.data?.findings.length === 0 ? (
            <EmptyState description="该次真实检查没有返回 Finding。" title="未发现结构问题" />
          ) : null}
          {check.data?.findings.map((finding) => (
            <article className="studio-finding" key={finding.id}>
              <div className="studio-panel__heading">
                <div>
                  <strong>{finding.finding_type}</strong>
                  <p className="studio-code-line">{finding.message_code}</p>
                </div>
                <div className="studio-action-row">
                  <StatusBadge status={finding.status} />
                  <Badge tone={finding.severity === "blocker" ? "danger" : "warning"}>
                    {finding.severity}
                  </Badge>
                </div>
              </div>
              <dl className="studio-definition-list studio-definition-list--compact">
                <div>
                  <dt>Finding ID</dt>
                  <dd className="studio-code-value">{finding.id}</dd>
                </div>
                <div>
                  <dt>证据引用</dt>
                  <dd className="studio-code-value">
                    {finding.evidence_references.join(", ") || "无"}
                  </dd>
                </div>
                <div>
                  <dt>验证器</dt>
                  <dd>
                    {finding.validator_key} / {finding.validator_version}
                  </dd>
                </div>
              </dl>
              {canWrite && finding.status === "open" ? (
                <Button
                  onClick={() => {
                    setSelectedFindingId(finding.id);
                  }}
                  variant={selectedFindingId === finding.id ? "primary" : "secondary"}
                >
                  {selectedFindingId === finding.id ? "已选择" : "为此项创建 Proposal"}
                </Button>
              ) : null}
            </article>
          ))}
        </section>
      ) : null}

      {selectedFindingId && canWrite ? (
        <section className="studio-panel">
          <div>
            <p className="studio-eyebrow">Resolution Proposal</p>
            <h2>创建受控修复提案</h2>
          </div>
          <form className="studio-form-grid" onSubmit={(event) => void submitResolution(event)}>
            <Input
              label="策略代码"
              onChange={(event) => {
                setStrategyCode(event.target.value);
              }}
              pattern="[a-z][a-z0-9_.-]*"
              required
              value={strategyCode}
            />
            <Input
              label="目标引用"
              onChange={(event) => {
                setTargetReference(event.target.value);
              }}
              placeholder="scheme://technical-target"
              required
              value={targetReference}
            />
            <Input
              label="目标期望版本"
              min={1}
              onChange={(event) => {
                setTargetVersion(event.target.value);
              }}
              required
              type="number"
              value={targetVersion}
            />
            <Button busy={createResolution.isPending} type="submit">
              创建 Proposal
            </Button>
          </form>
          {createResolution.isError ? (
            <InlineApiError error={createResolution.error} title="Proposal 创建失败" />
          ) : null}
        </section>
      ) : null}

      <section className="studio-two-column">
        <article className="studio-panel">
          <div>
            <p className="studio-eyebrow">Resolution</p>
            <h2>按 Proposal ID 读取</h2>
          </div>
          <form className="studio-form-row" onSubmit={lookupResolution}>
            <Input
              label="Resolution Proposal ID"
              onChange={(event) => {
                setResolutionLookup(event.target.value);
              }}
              required
              value={resolutionLookup}
            />
            <Button type="submit" variant="secondary">
              读取
            </Button>
          </form>
          {resolutionId && resolution.data ? (
            <>
              <div className="studio-panel__heading">
                <strong>{resolution.data.strategy_code}</strong>
                <StatusBadge status={resolution.data.status} />
              </div>
              <dl className="studio-definition-list studio-definition-list--compact">
                <div>
                  <dt>Finding</dt>
                  <dd className="studio-code-value">{resolution.data.finding_ids.join(", ")}</dd>
                </div>
                <div>
                  <dt>版本</dt>
                  <dd>{resolution.data.version}</dd>
                </div>
              </dl>
              {resolution.data.status === "proposed" && canDecide ? (
                <div className="studio-action-row">
                  <Button
                    onClick={() => {
                      setPendingDecision("approve");
                    }}
                  >
                    批准 Proposal
                  </Button>
                  <Button
                    onClick={() => {
                      setPendingDecision("reject");
                    }}
                    variant="danger"
                  >
                    拒绝 Proposal
                  </Button>
                </div>
              ) : null}
            </>
          ) : null}
          {resolution.isPending && resolutionId ? <p className="studio-muted">正在读取…</p> : null}
          {resolution.isError ? (
            <InlineApiError error={resolution.error} title="Resolution 读取失败" />
          ) : null}
          {decideResolution.isError ? (
            <InlineApiError error={decideResolution.error} title="Resolution 决定失败" />
          ) : null}
        </article>

        <article className="studio-panel">
          <div>
            <p className="studio-eyebrow">Quality</p>
            <h2>确定性质量评估</h2>
          </div>
          {canWrite ? (
            <form className="studio-form-stack" onSubmit={(event) => void submitQuality(event)}>
              <Input
                label="Rubric 代码"
                onChange={(event) => {
                  setRubricKey(event.target.value);
                }}
                pattern="[a-z][a-z0-9_.-]*"
                required
                value={rubricKey}
              />
              <Input
                label="Dimension 代码"
                onChange={(event) => {
                  setDimensionKey(event.target.value);
                }}
                pattern="[a-z][a-z0-9_.-]*"
                required
                value={dimensionKey}
              />
              <Input
                label="输入引用"
                onChange={(event) => {
                  setQualityReference(event.target.value);
                }}
                required
                value={qualityReference}
              />
              <Button busy={runQuality.isPending} type="submit">
                运行质量评估
              </Button>
            </form>
          ) : (
            <p className="studio-readonly-note">当前身份只能读取质量结果。</p>
          )}
          {runQuality.isError ? (
            <InlineApiError error={runQuality.error} title="质量评估失败" />
          ) : null}
          <form className="studio-form-row" onSubmit={lookupQuality}>
            <Input
              label="Evaluation Run ID"
              onChange={(event) => {
                setQualityRunLookup(event.target.value);
              }}
              required
              value={qualityRunLookup}
            />
            <Button type="submit" variant="secondary">
              读取
            </Button>
          </form>
          {quality.isPending && qualityRunId ? <p className="studio-muted">正在读取…</p> : null}
          {quality.isError ? (
            <InlineApiError error={quality.error} title="质量结果读取失败" />
          ) : null}
          {quality.data ? (
            <div className="studio-status-card">
              <div className="studio-panel__heading">
                <strong>{quality.data.evaluator_key}</strong>
                <StatusBadge status={quality.data.status} />
              </div>
              <ul className="studio-compact-list">
                {quality.data.dimensions.map((dimension) => (
                  <li key={dimension.key}>
                    {dimension.key}: {dimension.status}
                    {dimension.score === null ? "" : ` / ${String(dimension.score)}`}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </article>
      </section>

      <Dialog
        description="批准只改变 Proposal 状态，不会自动修改全部内容。服务端会校验权限和 If-Match。"
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
              busy={decideResolution.isPending}
              onClick={() => void confirmDecision()}
              variant={pendingDecision === "reject" ? "danger" : "primary"}
            >
              确认决定
            </Button>
          </div>
        }
        onOpenChange={(open) => {
          if (!open && !decideResolution.isPending) setPendingDecision(null);
        }}
        open={pendingDecision !== null}
        title={
          pendingDecision === "reject" ? "拒绝 Resolution Proposal" : "批准 Resolution Proposal"
        }
      >
        <p>终态竞争、403、409 与 429 会以服务端错误返回，不在浏览器中假定成功。</p>
      </Dialog>
    </section>
  );
}
