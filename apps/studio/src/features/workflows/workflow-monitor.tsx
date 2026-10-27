"use client";

import { Badge, Button, EmptyState, Input, Select } from "@accos/ui";
import { useRouter } from "next/navigation";
import { useState, type SyntheticEvent } from "react";

import { InlineApiError } from "../../components/inline-api-error";
import { StateResolver } from "../../components/state-resolver";
import { useCreateWorkflowRunMutation } from "../../lib/api/mutations";
import { useWorkflowDefinitionsQuery } from "../../lib/api/queries";
import { useIdentity } from "../../providers/identity-provider";
import { useProject } from "../../providers/scope-providers";
import { canRunAgents } from "../monitoring/status";
import { ProjectHeader } from "../projects/project-header";

const technicalSmokeReference = "fixture-token://framework-smoke";

export function WorkflowMonitor() {
  const identity = useIdentity();
  const project = useProject();
  const router = useRouter();
  const definitions = useWorkflowDefinitionsQuery();
  const createRun = useCreateWorkflowRunMutation(identity.workspace_id, project.id);
  const [workflowName, setWorkflowName] = useState("");
  const [inputReference, setInputReference] = useState(technicalSmokeReference);
  const [lookupRunId, setLookupRunId] = useState("");
  const canRun = canRunAgents(identity, project.status);

  if (definitions.isPending) return <StateResolver state="loading" />;
  if (definitions.isError) {
    return <StateResolver error={definitions.error} onRetry={() => void definitions.refetch()} />;
  }

  const selectedWorkflow =
    workflowName.length > 0 ? workflowName : (definitions.data.items[0]?.name ?? "");

  async function submitRun(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedWorkflow || !inputReference.trim()) return;
    const accepted = await createRun.mutateAsync({
      inputReference: inputReference.trim(),
      workflowName: selectedWorkflow,
    });
    router.push(`/projects/${project.id}/workflows/runs/${accepted.run_id}`);
  }

  function openKnownRun(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!lookupRunId.trim()) return;
    router.push(`/projects/${project.id}/workflows/runs/${lookupRunId.trim()}`);
  }

  return (
    <section className="studio-page studio-page--wide">
      <ProjectHeader active="workflows" eyebrow="Workflow Monitor" title="技术工作流监控" />

      <div className="studio-summary-strip">
        <div>
          <span>定义来源</span>
          <strong>Workflow API</strong>
        </div>
        <div>
          <span>可用定义</span>
          <strong>{definitions.data.items.length}</strong>
        </div>
        <div>
          <span>当前权限</span>
          <strong>{canRun ? "可提交" : "只读"}</strong>
        </div>
      </div>

      {definitions.data.items.length === 0 ? (
        <EmptyState
          description="服务端尚未注册可执行的 Workflow 定义。"
          title="暂无 Workflow 定义"
        />
      ) : (
        <section className="studio-two-column">
          <article className="studio-panel">
            <div className="studio-panel__heading">
              <div>
                <p className="studio-eyebrow">Definitions</p>
                <h2>服务端定义</h2>
              </div>
              <Badge tone="info">非在线状态</Badge>
            </div>
            <div className="studio-card-list">
              {definitions.data.items.map((definition) => (
                <article className="studio-status-card" key={definition.name}>
                  <div className="studio-panel__heading">
                    <strong>{definition.name}</strong>
                    <Badge tone="neutral">v{definition.version}</Badge>
                  </div>
                  <ol className="studio-compact-list">
                    {definition.step_keys.map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ol>
                </article>
              ))}
            </div>
          </article>

          <article className="studio-panel">
            <div>
              <p className="studio-eyebrow">Technical smoke</p>
              <h2>提交真实空链路</h2>
              <p className="studio-muted">
                framework_smoke 只传递技术引用，并由 Director、Workflow、Fake Agent 与 Fake Model
                的服务端链路处理。
              </p>
            </div>
            {canRun ? (
              <form className="studio-form-stack" onSubmit={(event) => void submitRun(event)}>
                <Select
                  label="Workflow 定义"
                  onChange={(event) => {
                    setWorkflowName(event.target.value);
                  }}
                  value={selectedWorkflow}
                >
                  {definitions.data.items.map((definition) => (
                    <option key={definition.name} value={definition.name}>
                      {definition.name} · v{definition.version}
                    </option>
                  ))}
                </Select>
                <Input
                  description="只接受 URI 形式的技术引用；不会提交创作正文。"
                  label="输入引用"
                  onChange={(event) => {
                    setInputReference(event.target.value);
                  }}
                  required
                  value={inputReference}
                />
                <Button busy={createRun.isPending} type="submit">
                  提交 framework_smoke
                </Button>
              </form>
            ) : (
              <p className="studio-readonly-note">
                当前身份没有 agent:run，或 Project 已归档；服务端仍会拒绝直接写调用。
              </p>
            )}
            {createRun.isError ? (
              <InlineApiError error={createRun.error} title="Workflow 提交失败" />
            ) : null}
          </article>
        </section>
      )}

      <section className="studio-panel studio-panel--compact">
        <div>
          <p className="studio-eyebrow">Recover</p>
          <h2>按 Run ID 恢复</h2>
          <p className="studio-muted">
            Run ID 来自 202 响应；刷新或断线后会重新读取服务端状态，不使用浏览器缓存充当事实源。
          </p>
        </div>
        <form className="studio-form-row" onSubmit={openKnownRun}>
          <Input
            label="Workflow Run ID"
            onChange={(event) => {
              setLookupRunId(event.target.value);
            }}
            required
            value={lookupRunId}
          />
          <Button type="submit" variant="secondary">
            打开 Run
          </Button>
        </form>
      </section>
    </section>
  );
}
