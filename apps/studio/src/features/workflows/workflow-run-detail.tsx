"use client";

import type { components } from "@accos/api-client";
import { Badge, Button, Dialog, EmptyState, Input, Table, TableBody, TableHead } from "@accos/ui";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { InlineApiError } from "../../components/inline-api-error";
import { StateResolver } from "../../components/state-resolver";
import {
  useCreateWorkflowRunMutation,
  useWorkflowApprovalDecisionMutation,
  useWorkflowControlMutation,
  type WorkflowControlAction,
} from "../../lib/api/mutations";
import {
  useWorkflowApprovalQuery,
  useWorkflowRunQuery,
  useWorkflowStepsQuery,
  useWorkflowTasksQuery,
} from "../../lib/api/queries";
import { useIdentity } from "../../providers/identity-provider";
import { useProject } from "../../providers/scope-providers";
import { StatusBadge } from "../monitoring/status-badge";
import {
  canDecideApprovals,
  canRunAgents,
  isWorkflowTerminal,
  toneForStatus,
} from "../monitoring/status";
import { useWorkflowStream } from "../monitoring/use-workflow-stream";
import { ProjectHeader } from "../projects/project-header";

type ApprovalDecision = components["schemas"]["WorkflowApprovalDecision"];
type PendingAction = ApprovalDecision | "cancel" | "pause" | "resume" | "retry" | null;

function actionTitle(action: PendingAction): string {
  if (action === "approve") return "批准当前等待步骤";
  if (action === "reject") return "拒绝当前等待步骤";
  if (action === "cancel") return "取消 Workflow Run";
  if (action === "pause") return "暂停 Workflow Run";
  if (action === "resume") return "恢复 Workflow Run";
  if (action === "retry") return "创建新的重试 Run";
  return "确认操作";
}

export function WorkflowRunDetail({ runId }: { runId: string }) {
  const identity = useIdentity();
  const project = useProject();
  const router = useRouter();
  const run = useWorkflowRunQuery(identity.workspace_id, runId);
  const steps = useWorkflowStepsQuery(identity.workspace_id, runId);
  const tasks = useWorkflowTasksQuery(identity.workspace_id, runId);
  const approval = useWorkflowApprovalQuery(
    identity.workspace_id,
    runId,
    run.data?.status === "waiting_approval",
  );
  const stream = useWorkflowStream(
    identity.workspace_id,
    runId,
    run.data?.project_id === project.id,
  );
  const control = useWorkflowControlMutation(identity.workspace_id, runId);
  const decide = useWorkflowApprovalDecisionMutation(identity.workspace_id, runId);
  const retry = useCreateWorkflowRunMutation(identity.workspace_id, project.id);
  const [pendingAction, setPendingAction] = useState<PendingAction>(null);
  const [reason, setReason] = useState("");

  if (run.isPending || steps.isPending || tasks.isPending) return <StateResolver state="loading" />;
  if (run.isError) return <StateResolver error={run.error} onRetry={() => void run.refetch()} />;
  if (run.data.project_id !== project.id) return <StateResolver state="forbidden" />;
  if (steps.isError)
    return <StateResolver error={steps.error} onRetry={() => void steps.refetch()} />;
  if (tasks.isError)
    return <StateResolver error={tasks.error} onRetry={() => void tasks.refetch()} />;

  const runData = run.data;
  const terminal = isWorkflowTerminal(runData.status);
  const canControl = canRunAgents(identity, project.status);
  const canDecide =
    canDecideApprovals(identity) &&
    approval.data?.can_decide === true &&
    approval.data?.status === "pending";
  const mutationError = control.error ?? decide.error ?? retry.error;
  const busy = control.isPending || decide.isPending || retry.isPending;

  async function confirmAction() {
    if (pendingAction === null) return;
    if (pendingAction === "approve" || pendingAction === "reject") {
      if (!reason.trim()) return;
      await decide.mutateAsync({ decision: pendingAction, reason: reason.trim() });
    } else if (pendingAction === "retry") {
      const accepted = await retry.mutateAsync({
        inputReference: runData.input_reference,
        workflowName: runData.definition_name,
      });
      router.push(`/projects/${project.id}/workflows/runs/${accepted.run_id}`);
    } else {
      await control.mutateAsync(pendingAction satisfies WorkflowControlAction);
    }
    setPendingAction(null);
    setReason("");
  }

  return (
    <section className="studio-page studio-page--wide">
      <ProjectHeader active="workflows" eyebrow="Workflow Run" title={run.data.definition_name} />

      <div className="studio-summary-strip">
        <div>
          <span>Run 状态</span>
          <strong>{run.data.status}</strong>
        </div>
        <div>
          <span>当前步骤</span>
          <strong>
            {run.data.current_step_position + 1} / {steps.data.items.length}
          </strong>
        </div>
        <div>
          <span>SSE</span>
          <strong>{stream.connectionState}</strong>
        </div>
      </div>

      <section className="studio-panel studio-panel--compact">
        <div className="studio-panel__heading">
          <div>
            <p className="studio-eyebrow">Server calibrated</p>
            <h2>运行控制</h2>
          </div>
          <StatusBadge status={run.data.status} />
        </div>
        <dl className="studio-definition-list">
          <div>
            <dt>Run ID</dt>
            <dd className="studio-code-value">{run.data.id}</dd>
          </div>
          <div>
            <dt>Correlation ID</dt>
            <dd className="studio-code-value">{run.data.correlation_id}</dd>
          </div>
          <div>
            <dt>输入引用</dt>
            <dd className="studio-code-value">{run.data.input_reference}</dd>
          </div>
          <div>
            <dt>输出引用</dt>
            <dd className="studio-code-value">{run.data.output_reference ?? "尚未产生"}</dd>
          </div>
          <div>
            <dt>失败原因</dt>
            <dd className="studio-code-value">{run.data.error_reference ?? "无"}</dd>
          </div>
          <div>
            <dt>状态版本</dt>
            <dd>{run.data.version}</dd>
          </div>
        </dl>
        {canControl ? (
          <div className="studio-action-row">
            {run.data.status === "running" || run.data.status === "pending" ? (
              <Button
                onClick={() => {
                  setPendingAction("pause");
                }}
                variant="secondary"
              >
                暂停
              </Button>
            ) : null}
            {run.data.status === "paused" ? (
              <Button
                onClick={() => {
                  setPendingAction("resume");
                }}
                variant="secondary"
              >
                恢复
              </Button>
            ) : null}
            {!terminal && run.data.status !== "cancelling" ? (
              <Button
                onClick={() => {
                  setPendingAction("cancel");
                }}
                variant="danger"
              >
                取消
              </Button>
            ) : null}
            {terminal ? (
              <Button
                onClick={() => {
                  setPendingAction("retry");
                }}
                variant="secondary"
              >
                重试为新 Run
              </Button>
            ) : null}
          </div>
        ) : (
          <p className="studio-readonly-note">当前身份只能读取服务端 Run 状态。</p>
        )}
        {mutationError ? <InlineApiError error={mutationError} title="状态修改失败" /> : null}
      </section>

      {run.data.status === "waiting_approval" ? (
        <section className="studio-panel">
          <div className="studio-panel__heading">
            <div>
              <p className="studio-eyebrow">Human gate</p>
              <h2>等待审批</h2>
            </div>
            <Badge tone="warning">必须显式决定</Badge>
          </div>
          {approval.isPending ? <StateResolver state="loading" /> : null}
          {approval.isError ? (
            <InlineApiError error={approval.error} title="审批请求读取失败" />
          ) : null}
          {approval.data ? (
            <>
              <dl className="studio-definition-list">
                <div>
                  <dt>审批请求</dt>
                  <dd className="studio-code-value">{approval.data.id}</dd>
                </div>
                <div>
                  <dt>过期时间</dt>
                  <dd>{approval.data.expires_at}</dd>
                </div>
              </dl>
              {canDecide ? (
                <div className="studio-action-row">
                  <Button
                    onClick={() => {
                      setPendingAction("approve");
                    }}
                  >
                    批准
                  </Button>
                  <Button
                    onClick={() => {
                      setPendingAction("reject");
                    }}
                    variant="danger"
                  >
                    拒绝
                  </Button>
                </div>
              ) : (
                <p className="studio-readonly-note">
                  当前会话不满足此请求冻结的审批策略，或审批已到期。个人确认与团队双人审批由服务端分别执行。
                </p>
              )}
            </>
          ) : null}
        </section>
      ) : null}

      <section className="studio-two-column">
        <article className="studio-panel">
          <div className="studio-panel__heading">
            <h2>步骤与尝试</h2>
            <Badge tone="neutral">{steps.data.items.length} 步</Badge>
          </div>
          {steps.data.items.length === 0 ? (
            <EmptyState description="服务端尚未创建 Step Run。" title="暂无步骤" />
          ) : (
            <Table caption="Workflow 步骤状态">
              <TableHead>
                <tr>
                  <th scope="col">位置</th>
                  <th scope="col">Step</th>
                  <th scope="col">尝试</th>
                  <th scope="col">状态</th>
                </tr>
              </TableHead>
              <TableBody>
                {steps.data.items.map((step) => (
                  <tr key={step.id}>
                    <td>{step.position + 1}</td>
                    <td className="studio-code-value">{step.step_key}</td>
                    <td>{step.attempt}</td>
                    <td>
                      <StatusBadge status={step.status} />
                    </td>
                  </tr>
                ))}
              </TableBody>
            </Table>
          )}
        </article>

        <article className="studio-panel">
          <div className="studio-panel__heading">
            <h2>队列任务</h2>
            <Badge tone="neutral">{tasks.data.items.length} 项</Badge>
          </div>
          {tasks.data.items.length === 0 ? (
            <EmptyState description="服务端尚未创建 Task Run。" title="暂无队列任务" />
          ) : (
            <Table caption="Workflow 队列任务状态">
              <TableHead>
                <tr>
                  <th scope="col">Task</th>
                  <th scope="col">尝试</th>
                  <th scope="col">可用时间</th>
                  <th scope="col">状态</th>
                </tr>
              </TableHead>
              <TableBody>
                {tasks.data.items.map((task) => (
                  <tr key={task.id}>
                    <td className="studio-code-value">{task.id}</td>
                    <td>{task.attempt}</td>
                    <td>{task.available_at}</td>
                    <td>
                      <StatusBadge status={task.status} />
                    </td>
                  </tr>
                ))}
              </TableBody>
            </Table>
          )}
        </article>
      </section>

      <section className="studio-panel">
        <div className="studio-panel__heading">
          <div>
            <p className="studio-eyebrow">Resumable SSE</p>
            <h2>持久事件流</h2>
          </div>
          <Badge
            tone={
              stream.connectionState === "open" ? "success" : toneForStatus(stream.connectionState)
            }
          >
            {stream.connectionState}
          </Badge>
        </div>
        {stream.cursorReset || stream.projection.resetRequired ? (
          <p className="studio-readonly-note">
            事件游标已过期或流需要重置；已清除游标并用状态 API 重新校准。
          </p>
        ) : null}
        {stream.error ? (
          <>
            <InlineApiError error={stream.error} title="实时事件连接失败" />
            <Button
              onClick={() => {
                stream.reconnect();
              }}
              variant="secondary"
            >
              重新连接
            </Button>
          </>
        ) : null}
        {stream.projection.events.length === 0 ? (
          <EmptyState
            description="连接已建立时会从服务端保留游标恢复；当前尚无可显示事件。"
            title="暂无 SSE 事件"
          />
        ) : (
          <ol className="studio-timeline">
            {stream.projection.events.map((event) => (
              <li key={event.event_id}>
                <div>
                  <strong>{event.type}</strong>
                  <span>#{event.sequence}</span>
                </div>
                <time dateTime={event.occurred_at}>{event.occurred_at}</time>
                <details>
                  <summary>查看技术载荷</summary>
                  <pre>{JSON.stringify(event.payload, null, 2)}</pre>
                </details>
              </li>
            ))}
          </ol>
        )}
      </section>

      <Dialog
        description="服务端会再次校验权限、状态版本与终态竞争。"
        footer={
          <div className="studio-action-row">
            <Button
              onClick={() => {
                setPendingAction(null);
                setReason("");
              }}
              variant="secondary"
            >
              返回
            </Button>
            <Button
              busy={busy}
              disabled={
                (pendingAction === "approve" || pendingAction === "reject") && !reason.trim()
              }
              onClick={() => void confirmAction()}
              variant={
                pendingAction === "cancel" || pendingAction === "reject" ? "danger" : "primary"
              }
            >
              确认
            </Button>
          </div>
        }
        onOpenChange={(open) => {
          if (!open && !busy) setPendingAction(null);
        }}
        open={pendingAction !== null}
        title={actionTitle(pendingAction)}
      >
        {pendingAction === "approve" || pendingAction === "reject" ? (
          <Input
            label="决定理由"
            maxLength={500}
            onChange={(event) => {
              setReason(event.target.value);
            }}
            required
            value={reason}
          />
        ) : (
          <p>此操作不会在浏览器中预设结果；完成后页面会读取服务端最终状态。</p>
        )}
      </Dialog>
    </section>
  );
}
