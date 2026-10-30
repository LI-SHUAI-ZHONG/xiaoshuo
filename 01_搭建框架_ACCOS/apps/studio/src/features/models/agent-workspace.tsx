"use client";

import { Button, Input, Select, Table, TableBody, TableHead } from "@accos/ui";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { StateResolver } from "../../components/state-resolver";
import { useIdentity } from "../../providers/identity-provider";
import { useProject } from "../../providers/scope-providers";
import { ProjectHeader } from "../projects/project-header";
import { StatusBadge } from "../monitoring/status-badge";
import { ContentPicker } from "./content-picker";
import { pinKey, terminalCall, useModelApi, type AgentTask, type ContentRef } from "./model-api";
import { TextArea, pretty, useAction } from "./model-common";

function AgentJobDetail({ id }: { id: string }) {
  const identity = useIdentity();
  const project = useProject();
  const api = useModelApi(identity.workspace_id, project.id);
  const key = ["agent-job", identity.actor_id, identity.workspace_id, project.id, id];
  const job = useQuery({
    queryKey: key,
    queryFn: () => api.job(id),
    refetchInterval: (q) => (q.state.data && terminalCall(q.state.data.status) ? false : 1500),
  });
  const [kind, setKind] = useState<"input" | "output">("output");
  const available = kind === "input" || Boolean(job.data?.result_reference);
  const content = useQuery({
    queryKey: [...key, kind, job.data?.updated_at],
    queryFn: () => api.jobContent(id, kind),
    enabled: Boolean(job.data) && available,
  });
  if (job.isPending) return <StateResolver state="loading" />;
  if (job.isError) return <StateResolver error={job.error} onRetry={() => void job.refetch()} />;
  return (
    <article className="studio-panel">
      <div className="studio-panel__heading">
        <h2>Agent 任务详情</h2>
        <StatusBadge status={job.data.status} />
      </div>
      <p className="studio-code-value">{id}</p>
      <p>
        结果类型：{job.data.result_kind ?? "待生成"} · {job.data.error_code ?? "无错误"}
      </p>
      <p>Agent 产出为待审候选。规划结果仅通过结构与依赖校验，尚未批准或执行后续创作。</p>
      <Select
        label="任务内容"
        value={kind}
        onChange={(e) => setKind(e.target.value as typeof kind)}
      >
        <option value="output">候选结果</option>
        <option value="input">冻结任务与版本</option>
      </Select>
      {!available ? (
        <p>候选结果尚未产生。可从模型调用历史查看已发生的尝试和暂存内容。</p>
      ) : content.isPending ? (
        <StateResolver state="loading" />
      ) : content.isError ? (
        <StateResolver error={content.error} onRetry={() => void content.refetch()} />
      ) : (
        <pre className="model-content">{content.data.text}</pre>
      )}
      <Link className="studio-link-button" href={"/projects/" + project.id + "/models"}>
        查看调用与用量
      </Link>
    </article>
  );
}

export function RealAgentCenter() {
  const identity = useIdentity();
  const project = useProject();
  const api = useModelApi(identity.workspace_id, project.id);
  const router = useRouter();
  const selected = useSearchParams().get("job") ?? "";
  const scope = [identity.actor_id, identity.workspace_id, project.id];
  const config = useQuery({
    queryKey: ["agent-task-options", ...scope],
    queryFn: async () => {
      const [agents, policies, prompts] = await Promise.all([
        api.agents(),
        api.policies(),
        api.prompts(),
      ]);
      return { agents: agents.items, policies, prompts };
    },
  });
  const history = useInfiniteQuery({
    queryKey: ["agent-task-history", ...scope],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => api.jobs(pageParam),
    getNextPageParam: (p) => p.next_cursor ?? undefined,
    refetchInterval: (q) =>
      q.state.data?.pages.some((p) => p.items.some((j) => !terminalCall(j.status))) ? 2000 : false,
  });
  const [agent, setAgent] = useState("assistant");
  const [policy, setPolicy] = useState("");
  const [prompt, setPrompt] = useState("");
  const [task, setTask] = useState("");
  const [constraints, setConstraints] = useState("");
  const [privacy, setPrivacy] = useState<"local_only" | "workspace">("local_only");
  const [refs, setRefs] = useState<ContentRef[]>([]);
  const [tools, setTools] = useState(false);
  const [steps, setSteps] = useState("8");
  const [calls, setCalls] = useState("12");
  const [tokens, setTokens] = useState("32000");
  const [seconds, setSeconds] = useState("300");
  const pending = useRef<{ fingerprint: string; operation: string } | null>(null);
  const action = useAction();
  const canRun =
    project.status === "active" &&
    ["model:run", "agent:run"].every((p) => identity.permissions.includes(p));
  const descriptor = config.data?.agents.find((a) => a.agent_id === agent);
  const availablePrompts =
    config.data?.prompts.filter((p) => descriptor?.capabilities.includes(p.id)) ?? [];
  const jobs = history.data?.pages.flatMap((p) => p.items) ?? [];
  function open(id: string) {
    router.replace("/projects/" + project.id + "/agents?job=" + encodeURIComponent(id), {
      scroll: false,
    });
  }
  return (
    <section className="studio-page studio-page--wide">
      <ProjectHeader active="agents" eyebrow="真实任务执行" title="Agent 任务与候选结果" />
      <p>
        <Link className="studio-link-button" href="/settings/models">
          配置模型与预算
        </Link>{" "}
        <Link className="studio-link-button" href="/settings/prompts">
          配置 Prompt
        </Link>
      </p>
      {config.isPending ? (
        <StateResolver state="loading" />
      ) : config.isError ? (
        <StateResolver error={config.error} onRetry={() => void config.refetch()} />
      ) : (
        <form
          className="studio-panel studio-form-stack"
          onSubmit={(e) => {
            e.preventDefault();
            void action.run(async () => {
              const policyValue = config.data.policies.find((p) => pinKey(p) === policy);
              const promptValue = availablePrompts.find((p) => pinKey(p) === prompt);
              if (!policyValue || !promptValue)
                throw new Error("请选择已发布的策略和适用 Prompt 版本。");
              const values = {
                agent,
                policy,
                prompt,
                task,
                constraints,
                privacy,
                refs,
                tools,
                steps,
                calls,
                tokens,
                seconds,
              };
              const fingerprint = pretty(values);
              if (pending.current?.fingerprint !== fingerprint)
                pending.current = { fingerprint, operation: crypto.randomUUID() };
              const body: AgentTask = {
                operation_key: pending.current.operation,
                agent_id: agent,
                task,
                constraints,
                privacy,
                content_refs: refs,
                policy: { id: policyValue.id, version: policyValue.version },
                prompt: {
                  id: promptValue.id,
                  version: promptValue.version,
                  checksum: promptValue.checksum ?? "",
                },
                tools: tools ? ["content.read"] : [],
                max_steps: Number(steps),
                max_calls: Number(calls),
                max_tokens: Number(tokens),
                timeout_seconds: Number(seconds),
              };
              const result = await api.submitAgent(body);
              pending.current = null;
              open(result.id);
              await history.refetch();
            }, "Agent 任务已排队；输入、Prompt 和模型策略已固定。");
          }}
        >
          <h2>提交任务</h2>
          <fieldset className="model-fieldset studio-form-stack" disabled={!canRun || action.busy}>
            <div className="studio-form-grid">
              <Select
                label="任务角色"
                required
                value={agent}
                onChange={(e) => {
                  setAgent(e.target.value);
                  setPrompt("");
                }}
              >
                <option value="">选择角色</option>
                {config.data.agents.map((a) => (
                  <option key={a.agent_id} value={a.agent_id}>
                    {a.agent_id} · {a.capabilities.join("、")}
                  </option>
                ))}
              </Select>
              <Select
                label="Prompt 版本"
                required
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
              >
                <option value="">选择适用版本</option>
                {availablePrompts.map((p) => (
                  <option key={pinKey(p)} value={pinKey(p)}>
                    {p.title} · {pinKey(p)}
                  </option>
                ))}
              </Select>
              <Select
                label="模型策略版本"
                required
                value={policy}
                onChange={(e) => setPolicy(e.target.value)}
              >
                <option value="">选择策略</option>
                {config.data.policies
                  .filter((p) => p.enabled)
                  .map((p) => (
                    <option key={pinKey(p)} value={pinKey(p)}>
                      {p.label} · {pinKey(p)}
                    </option>
                  ))}
              </Select>
              <Select
                label="内容权限"
                value={privacy}
                onChange={(e) => setPrivacy(e.target.value as typeof privacy)}
              >
                <option value="local_only">仅本地</option>
                <option value="workspace">遵循工作区外发策略</option>
              </Select>
            </div>
            <TextArea
              label="任务目标与原话"
              required
              maxLength={100000}
              rows={6}
              value={task}
              onChange={(e) => setTask(e.target.value)}
            />
            <TextArea
              label="约束与停止条件"
              maxLength={20000}
              rows={3}
              value={constraints}
              onChange={(e) => setConstraints(e.target.value)}
            />
            <ContentPicker
              workspace={identity.workspace_id}
              project={project.id}
              value={refs}
              onChange={setRefs}
            />
            <label>
              <input
                type="checkbox"
                checked={tools}
                disabled={!identity.permissions.includes("tool:run")}
                onChange={(e) => setTools(e.target.checked)}
              />
              允许重新读取所选资料（content.read）
            </label>
            <div className="studio-form-grid">
              <Input
                label="最大执行轮次"
                type="number"
                min={1}
                max={16}
                required
                value={steps}
                onChange={(e) => setSteps(e.target.value)}
              />
              <Input
                label="模型与工具总调用上限"
                type="number"
                min={1}
                max={24}
                required
                value={calls}
                onChange={(e) => setCalls(e.target.value)}
              />
              <Input
                label="总 Token 上限"
                type="number"
                min={1024}
                max={128000}
                required
                value={tokens}
                onChange={(e) => setTokens(e.target.value)}
              />
              <Input
                label="任务超时（秒）"
                type="number"
                min={1}
                max={600}
                required
                value={seconds}
                onChange={(e) => setSeconds(e.target.value)}
              />
            </div>
            <Button type="submit">提交真实 Agent 任务</Button>
          </fieldset>
          {!canRun ? <p>当前身份需要 agent:run 和 model:run 权限，且项目处于活动状态。</p> : null}
          {descriptor ? (
            <p>
              可用任务：{descriptor.capabilities.join("、")} · 允许工具：
              {descriptor.allowed_tool_ids.join("、")}。正文与证据作为资料传入，不授予修改 Canon
              或发布的权限。
            </p>
          ) : null}
        </form>
      )}
      {action.notice}
      <section className="studio-panel">
        <div className="studio-panel__heading">
          <h2>任务历史</h2>
          <Button variant="secondary" onClick={() => void history.refetch()}>
            刷新历史
          </Button>
        </div>
        {history.isPending ? (
          <StateResolver state="loading" />
        ) : history.isError ? (
          <StateResolver error={history.error} onRetry={() => void history.refetch()} />
        ) : jobs.length ? (
          <Table caption="Agent 后台任务">
            <TableHead>
              <tr>
                <th>创建时间</th>
                <th>状态</th>
                <th>结果 / 错误</th>
                <th>操作</th>
              </tr>
            </TableHead>
            <TableBody>
              {jobs.map((j) => (
                <tr key={j.id}>
                  <td>{new Date(j.created_at).toLocaleString("zh-CN")}</td>
                  <td>
                    <StatusBadge status={j.status} />
                  </td>
                  <td>{j.result_kind ?? j.error_code ?? "等待结果"}</td>
                  <td>
                    <Button variant="secondary" onClick={() => open(j.id)}>
                      打开任务
                    </Button>
                  </td>
                </tr>
              ))}
            </TableBody>
          </Table>
        ) : (
          <p>暂无任务。新任务的输入和结果会保存在本项目中，刷新后可重新打开。</p>
        )}
        {history.hasNextPage ? (
          <Button busy={history.isFetchingNextPage} onClick={() => void history.fetchNextPage()}>
            加载更早的任务
          </Button>
        ) : null}
      </section>
      {selected ? <AgentJobDetail key={selected} id={selected} /> : null}
    </section>
  );
}
