"use client";

import type { components } from "@accos/api-client";
import { Badge, Button, EmptyState, Input, Table, TableBody, TableHead } from "@accos/ui";
import Link from "next/link";
import { useState, type SyntheticEvent } from "react";

import { InlineApiError } from "../../components/inline-api-error";
import { StateResolver } from "../../components/state-resolver";
import { useCreateDirectorRunMutation } from "../../lib/api/mutations";
import {
  useAgentRunQuery,
  useAgentsQuery,
  useModelStatusQuery,
  useToolStatusQuery,
} from "../../lib/api/queries";
import { useIdentity } from "../../providers/identity-provider";
import { useProject } from "../../providers/scope-providers";
import { StatusBadge } from "../monitoring/status-badge";
import { canRunAgents } from "../monitoring/status";
import { ProjectHeader } from "../projects/project-header";
import { RealAgentCenter } from "../models/agent-workspace";

type AsyncRunReference = components["schemas"]["AsyncRunReference"];
type AgentDescriptor = components["schemas"]["AgentDescriptorResponse"];

function workflowIdFromEventsUrl(eventsUrl: string | null | undefined): string | null {
  if (!eventsUrl) return null;
  const query = eventsUrl.split("?", 2)[1];
  return query ? new URLSearchParams(query).get("run_id") : null;
}

function descriptorConfiguration(
  descriptor: AgentDescriptor,
  providerCount: number,
  configuredTools: ReadonlySet<string>,
): "NOT_CONFIGURED" | "REGISTERED" {
  const toolsReady = descriptor.allowed_tool_ids.every((toolId) => configuredTools.has(toolId));
  return providerCount > 0 && toolsReady ? "REGISTERED" : "NOT_CONFIGURED";
}

export function AgentCenter() {
  const query = useAgentsQuery();
  if (query.isPending) return <StateResolver state="loading" />;
  if (query.isError) return <StateResolver error={query.error} onRetry={() => void query.refetch()} />;
  return query.data.items.some((a) => a.version.startsWith("1.")) ? <LegacyAgentCenter /> : <RealAgentCenter />;
}

function LegacyAgentCenter() {
  const identity = useIdentity();
  const project = useProject();
  const agents = useAgentsQuery();
  const models = useModelStatusQuery();
  const tools = useToolStatusQuery();
  const createRun = useCreateDirectorRunMutation(identity.workspace_id, project.id);
  const [accepted, setAccepted] = useState<AsyncRunReference | null>(null);
  const [agentRunId, setAgentRunId] = useState("");
  const [lookupId, setLookupId] = useState("");
  const [goalReference, setGoalReference] = useState("fixture-goal://framework-smoke");
  const [maxSteps, setMaxSteps] = useState("4");
  const [maxCalls, setMaxCalls] = useState("8");
  const [maxTokens, setMaxTokens] = useState("2048");
  const agentRun = useAgentRunQuery(identity.workspace_id, agentRunId);
  const canRun = canRunAgents(identity, project.status);

  if (agents.isPending || models.isPending || tools.isPending)
    return <StateResolver state="loading" />;
  if (agents.isError)
    return <StateResolver error={agents.error} onRetry={() => void agents.refetch()} />;
  if (models.isError)
    return <StateResolver error={models.error} onRetry={() => void models.refetch()} />;
  if (tools.isError)
    return <StateResolver error={tools.error} onRetry={() => void tools.refetch()} />;

  const configuredTools = new Set(
    tools.data.tools.filter((tool) => tool.configured).map((tool) => tool.tool_id),
  );
  const workflowRunId = workflowIdFromEventsUrl(accepted?.events_url);

  async function submitDirector(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    const result = await createRun.mutateAsync({
      goal_reference: goalReference.trim(),
      max_calls: Number(maxCalls),
      max_steps: Number(maxSteps),
      max_tokens: Number(maxTokens),
    });
    setAccepted(result);
    setAgentRunId(result.run_id);
  }

  function lookupRun(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setAccepted(null);
    setAgentRunId(lookupId.trim());
  }

  return (
    <section className="studio-page studio-page--wide">
      <ProjectHeader active="agents" eyebrow="Agent Center" title="Agent 注册与运行状态" />

      <div className="studio-summary-strip">
        <div>
          <span>注册 Descriptor</span>
          <strong>{agents.data.items.length}</strong>
        </div>
        <div>
          <span>模型 Provider</span>
          <strong>{models.data.providers.length}</strong>
        </div>
        <div>
          <span>已配置工具</span>
          <strong>{configuredTools.size}</strong>
        </div>
      </div>

      <p className="studio-readonly-note">
        REGISTERED 仅表示描述符及其当前依赖可配置；本页不会把注册记录误报为在线 Agent。
      </p>

      {agents.data.items.length === 0 ? (
        <EmptyState
          description="服务端 Agent Registry 返回空集合。"
          title="暂无 Agent Descriptor"
        />
      ) : (
        <section className="studio-card-list studio-card-list--columns">
          {agents.data.items.map((descriptor) => {
            const configuration = descriptorConfiguration(
              descriptor,
              models.data.providers.length,
              configuredTools,
            );
            return (
              <article
                className="studio-panel"
                key={`${descriptor.agent_id}:${descriptor.version}`}
              >
                <div className="studio-panel__heading">
                  <div>
                    <p className="studio-eyebrow">Descriptor</p>
                    <h2>{descriptor.agent_id}</h2>
                  </div>
                  <Badge tone={configuration === "REGISTERED" ? "info" : "warning"}>
                    {configuration}
                  </Badge>
                </div>
                <dl className="studio-definition-list studio-definition-list--compact">
                  <div>
                    <dt>版本</dt>
                    <dd>{descriptor.version}</dd>
                  </div>
                  <div>
                    <dt>模型策略</dt>
                    <dd className="studio-code-value">
                      {descriptor.model_policy_id} / {descriptor.model_policy_version}
                    </dd>
                  </div>
                  <div>
                    <dt>能力</dt>
                    <dd>{descriptor.capabilities.join(", ") || "无"}</dd>
                  </div>
                  <div>
                    <dt>允许工具</dt>
                    <dd>{descriptor.allowed_tool_ids.join(", ") || "无"}</dd>
                  </div>
                </dl>
                <div className="studio-budget-grid">
                  <span>steps ≤ {descriptor.budget_limit.max_steps}</span>
                  <span>calls ≤ {descriptor.budget_limit.max_calls}</span>
                  <span>tokens ≤ {descriptor.budget_limit.max_tokens}</span>
                  <span>parallel ≤ {descriptor.budget_limit.max_parallelism}</span>
                  <span>recursion ≤ {descriptor.budget_limit.max_recursion_depth}</span>
                  <span>seconds ≤ {descriptor.budget_limit.max_duration_seconds}</span>
                </div>
              </article>
            );
          })}
        </section>
      )}

      <section className="studio-two-column">
        <article className="studio-panel">
          <div>
            <p className="studio-eyebrow">Fake-safe run</p>
            <h2>提交 Director Run</h2>
          </div>
          {canRun ? (
            <form className="studio-form-stack" onSubmit={(event) => void submitDirector(event)}>
              <Input
                description="只提交技术 URI 引用。"
                label="Goal 引用"
                onChange={(event) => {
                  setGoalReference(event.target.value);
                }}
                required
                value={goalReference}
              />
              <div className="studio-form-grid studio-form-grid--three">
                <Input
                  label="最大步骤"
                  max={100}
                  min={1}
                  onChange={(event) => {
                    setMaxSteps(event.target.value);
                  }}
                  required
                  type="number"
                  value={maxSteps}
                />
                <Input
                  label="最大调用"
                  max={1000}
                  min={1}
                  onChange={(event) => {
                    setMaxCalls(event.target.value);
                  }}
                  required
                  type="number"
                  value={maxCalls}
                />
                <Input
                  label="最大 Token"
                  max={1_000_000}
                  min={1}
                  onChange={(event) => {
                    setMaxTokens(event.target.value);
                  }}
                  required
                  type="number"
                  value={maxTokens}
                />
              </div>
              <Button busy={createRun.isPending} type="submit">
                提交 Director Run
              </Button>
            </form>
          ) : (
            <p className="studio-readonly-note">当前身份没有 agent:run，Agent 写入口已隐藏。</p>
          )}
          {createRun.isError ? (
            <InlineApiError error={createRun.error} title="Agent Run 提交失败" />
          ) : null}
        </article>

        <article className="studio-panel">
          <div>
            <p className="studio-eyebrow">Recover</p>
            <h2>按 Agent Run ID 读取</h2>
          </div>
          <form className="studio-form-row" onSubmit={lookupRun}>
            <Input
              label="Agent Run ID"
              onChange={(event) => {
                setLookupId(event.target.value);
              }}
              required
              value={lookupId}
            />
            <Button type="submit" variant="secondary">
              读取
            </Button>
          </form>
          {accepted ? (
            <p className="studio-success-text">
              服务端已接受 Run <span className="studio-code-value">{accepted.run_id}</span>。
            </p>
          ) : null}
          {workflowRunId ? (
            <Link
              className="studio-link-button"
              href={`/projects/${project.id}/workflows/runs/${workflowRunId}`}
            >
              打开关联 Workflow
            </Link>
          ) : null}
        </article>
      </section>

      {agentRunId ? (
        <section className="studio-panel">
          <div className="studio-panel__heading">
            <div>
              <p className="studio-eyebrow">Agent Run</p>
              <h2>真实用量与终态</h2>
            </div>
            {agentRun.data ? <StatusBadge status={agentRun.data.status} /> : null}
          </div>
          {agentRun.isPending ? <StateResolver state="loading" /> : null}
          {agentRun.isError ? (
            <InlineApiError error={agentRun.error} title="Agent Run 读取失败" />
          ) : null}
          {agentRun.data ? (
            <>
              <div className="studio-metric-grid">
                <article className="studio-metric-card">
                  <span>模型调用</span>
                  <strong>{agentRun.data.model_calls}</strong>
                </article>
                <article className="studio-metric-card">
                  <span>工具调用</span>
                  <strong>{agentRun.data.tool_calls}</strong>
                </article>
                <article className="studio-metric-card">
                  <span>Token</span>
                  <strong>{agentRun.data.tokens}</strong>
                </article>
              </div>
              <dl className="studio-definition-list">
                <div>
                  <dt>Agent / 版本</dt>
                  <dd>
                    {agentRun.data.agent_id} / {agentRun.data.agent_version}
                  </dd>
                </div>
                <div>
                  <dt>尝试</dt>
                  <dd>{agentRun.data.attempt}</dd>
                </div>
                <div>
                  <dt>结果引用</dt>
                  <dd className="studio-code-value">
                    {agentRun.data.result_reference ?? "尚未产生"}
                  </dd>
                </div>
                <div>
                  <dt>错误码</dt>
                  <dd>{agentRun.data.error_code ?? "无"}</dd>
                </div>
              </dl>
            </>
          ) : null}
        </section>
      ) : null}

      <section className="studio-two-column">
        <article className="studio-panel">
          <div className="studio-panel__heading">
            <h2>模型 Provider</h2>
            <Badge tone="neutral">{models.data.protocol_version}</Badge>
          </div>
          {models.data.providers.length === 0 ? (
            <EmptyState description="模型网关未返回 Provider。" title="NOT_CONFIGURED" />
          ) : (
            <Table caption="模型 Provider 状态">
              <TableHead>
                <tr>
                  <th scope="col">Provider</th>
                  <th scope="col">能力</th>
                  <th scope="col">并发</th>
                  <th scope="col">状态</th>
                </tr>
              </TableHead>
              <TableBody>
                {models.data.providers.map((provider) => (
                  <tr key={provider.provider_id}>
                    <td>{provider.provider_id}</td>
                    <td>{provider.capabilities.join(", ")}</td>
                    <td>{provider.in_flight}</td>
                    <td>
                      <StatusBadge status={provider.state} />
                    </td>
                  </tr>
                ))}
              </TableBody>
            </Table>
          )}
        </article>

        <article className="studio-panel">
          <div className="studio-panel__heading">
            <h2>工具权限与配置</h2>
            <Badge tone="neutral">{tools.data.protocol_version}</Badge>
          </div>
          {tools.data.tools.length === 0 ? (
            <EmptyState description="工具网关未返回工具。" title="NOT_CONFIGURED" />
          ) : (
            <Table caption="工具配置状态">
              <TableHead>
                <tr>
                  <th scope="col">Tool</th>
                  <th scope="col">能力</th>
                  <th scope="col">幂等</th>
                  <th scope="col">配置</th>
                </tr>
              </TableHead>
              <TableBody>
                {tools.data.tools.map((tool) => (
                  <tr key={tool.tool_id}>
                    <td>{tool.tool_id}</td>
                    <td>{tool.capabilities.join(", ")}</td>
                    <td>{tool.idempotent ? "是" : "否"}</td>
                    <td>
                      <StatusBadge status={tool.configured ? "configured" : "not_configured"} />
                    </td>
                  </tr>
                ))}
              </TableBody>
            </Table>
          )}
        </article>
      </section>
    </section>
  );
}
