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
import { ModelCallDetail } from "./call-detail";
import {
  money,
  pinKey,
  terminalCall,
  useModelApi,
  type ContentRef,
  type Invocation,
} from "./model-api";
import { TextArea, objectJson, useAction } from "./model-common";

export function ModelWorkspace() {
  const identity = useIdentity();
  const project = useProject();
  const api = useModelApi(identity.workspace_id, project.id);
  const router = useRouter();
  const selected = useSearchParams().get("call") ?? "";
  const scope = [identity.actor_id, identity.workspace_id, project.id];
  const config = useQuery({
    queryKey: ["model-configuration-choices", ...scope],
    queryFn: async () => ({ policies: await api.policies(), prompts: await api.prompts() }),
  });
  const history = useInfiniteQuery({
    queryKey: ["model-history", ...scope],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => api.calls(pageParam),
    getNextPageParam: (p) => p.next_cursor ?? undefined,
    refetchInterval: (q) =>
      q.state.data?.pages.some((p) => p.items.some((c) => !terminalCall(c.status))) ? 2000 : false,
  });
  const [text, setText] = useState("");
  const [policy, setPolicy] = useState("");
  const [prompt, setPrompt] = useState("");
  const [kind, setKind] = useState<"generate" | "embed">("generate");
  const [privacy, setPrivacy] = useState<"local_only" | "workspace">("local_only");
  const [stream, setStream] = useState(true);
  const [cache, setCache] = useState(false);
  const [tokens, setTokens] = useState("2048");
  const [refs, setRefs] = useState<ContentRef[]>([]);
  const [variables, setVariables] = useState("{}");
  const [compare, setCompare] = useState("");
  const pending = useRef<{ fingerprint: string; operation: string } | null>(null);
  const action = useAction();
  const canRun = project.status === "active" && identity.permissions.includes("model:run");
  const calls = history.data?.pages.flatMap((p) => p.items) ?? [];
  function open(id: string) {
    router.replace("/projects/" + project.id + "/models?call=" + encodeURIComponent(id), {
      scroll: false,
    });
  }
  return (
    <section className="studio-page studio-page--wide">
      <ProjectHeader active="models" eyebrow="模型运行" title="模型调用与比较" />
      <p>
        <Link className="studio-link-button" href="/settings/models">
          模型与预算设置
        </Link>{" "}
        <Link className="studio-link-button" href="/settings/prompts">
          Prompt 模板
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
              if (!policyValue) throw new Error("请选择已发布策略。");
              const promptValue = config.data.prompts.find((p) => pinKey(p) === prompt);
              const input = {
                text,
                policy,
                prompt,
                kind,
                privacy,
                stream,
                cache,
                tokens,
                refs,
                variables,
              };
              const fingerprint = JSON.stringify(input);
              if (pending.current?.fingerprint !== fingerprint)
                pending.current = { fingerprint, operation: crypto.randomUUID() };
              const messages =
                promptValue && kind === "generate"
                  ? await api.preview(promptValue, promptValue.allowed_tasks[0] ?? "agent.task", {
                      task: text,
                      context: "[]",
                      constraints: "",
                      available_tools: [],
                      available_workflows: [],
                      ...objectJson(variables),
                    })
                  : [{ role: "user" as const, text, tool_calls: [], provider_items: [] }];
              const request: Invocation = {
                operation_key: pending.current.operation,
                schema_version: 2,
                policy: { id: policyValue.id, version: policyValue.version },
                messages: [
                  ...messages,
                  ...refs.map((ref) => ({
                    role: "user" as const,
                    content_ref: ref,
                    tool_calls: [],
                    provider_items: [],
                  })),
                ],
                task_kind:
                  promptValue && kind === "generate"
                    ? (promptValue.allowed_tasks[0] ?? "agent.task")
                    : "agent.task",
                prompt:
                  promptValue && kind === "generate"
                    ? {
                        id: promptValue.id,
                        version: promptValue.version,
                        checksum: promptValue.checksum ?? "",
                      }
                    : null,
                output_schema:
                  promptValue && kind === "generate" ? promptValue.output_schema : null,
                max_output_tokens: Number(tokens),
                privacy,
                kind,
                stream: kind === "generate" && stream,
                cache: Boolean(promptValue) && kind === "generate" && cache,
                parameters: {},
                tools: [],
              };
              const accepted = await api.submit(request);
              pending.current = null;
              open(accepted.call.id);
              await history.refetch();
            }, "调用已排队。刷新或关闭页面不会取消后台任务。");
          }}
        >
          <h2>新建调用</h2>
          <fieldset disabled={!canRun || action.busy} className="model-fieldset studio-form-stack">
            <div className="studio-form-grid">
              <Select
                label="策略版本"
                required
                value={policy}
                onChange={(e) => setPolicy(e.target.value)}
              >
                <option value="">请选择</option>
                {config.data.policies
                  .filter((p) => p.enabled)
                  .map((p) => (
                    <option key={pinKey(p)} value={pinKey(p)}>
                      {p.label} · {pinKey(p)}
                    </option>
                  ))}
              </Select>
              <Select
                label="调用类型"
                value={kind}
                onChange={(e) => setKind(e.target.value as typeof kind)}
              >
                <option value="generate">文本生成</option>
                <option value="embed">文本向量</option>
              </Select>
              <Select
                label="Prompt 版本"
                disabled={kind === "embed"}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
              >
                <option value="">直接输入</option>
                {config.data.prompts.map((p) => (
                  <option key={pinKey(p)} value={pinKey(p)}>
                    {p.title} · {pinKey(p)}
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
              label={kind === "embed" ? "需要向量化的文本" : "任务正文"}
              required
              rows={6}
              maxLength={100000}
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
            <ContentPicker
              workspace={identity.workspace_id}
              project={project.id}
              value={refs}
              onChange={setRefs}
            />
            {kind === "generate" ? (
              <>
                <Input
                  label="输出 Token 上限"
                  required
                  type="number"
                  min={1}
                  max={1000000}
                  value={tokens}
                  onChange={(e) => setTokens(e.target.value)}
                />
                <div className="model-options">
                  <label>
                    <input
                      type="checkbox"
                      checked={stream}
                      onChange={(e) => setStream(e.target.checked)}
                    />
                    流式生成
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={cache}
                      disabled={!prompt}
                      onChange={(e) => setCache(e.target.checked)}
                    />
                    允许相同版本与输入缓存
                  </label>
                </div>
                {prompt ? (
                  <details>
                    <summary>模板额外变量</summary>
                    <TextArea
                      label="变量覆盖 JSON"
                      rows={5}
                      value={variables}
                      onChange={(e) => setVariables(e.target.value)}
                    />
                  </details>
                ) : null}
              </>
            ) : null}
            <Button type="submit">提交真实模型调用</Button>
          </fieldset>
          {!canRun ? <p>当前身份无 model:run 权限，或项目已归档。</p> : null}
          {!config.data.policies.length ? (
            <p>CONFIG_REQUIRED：先发布模型配置、策略与预算。</p>
          ) : null}
        </form>
      )}
      {action.notice}
      <section className="studio-panel">
        <div className="studio-panel__heading">
          <h2>持久调用历史</h2>
          <Button variant="secondary" onClick={() => void history.refetch()}>
            刷新历史
          </Button>
        </div>
        {history.isPending ? (
          <StateResolver state="loading" />
        ) : history.isError ? (
          <StateResolver error={history.error} onRetry={() => void history.refetch()} />
        ) : calls.length ? (
          <Table caption="项目模型调用">
            <TableHead>
              <tr>
                <th>创建时间 / 任务</th>
                <th>模型版本</th>
                <th>状态</th>
                <th>费用</th>
                <th>查看</th>
              </tr>
            </TableHead>
            <TableBody>
              {calls.map((c) => (
                <tr key={c.id}>
                  <td>
                    {new Date(c.created_at).toLocaleString("zh-CN")}
                    <br />
                    {c.task_kind}
                  </td>
                  <td>{c.profile ? pinKey(c.profile) : "等待路由"}</td>
                  <td>
                    <StatusBadge status={c.status} />
                  </td>
                  <td>{money(c.cost_micro_usd)}</td>
                  <td>
                    <Button variant="secondary" onClick={() => open(c.id)}>
                      详情
                    </Button>
                  </td>
                </tr>
              ))}
            </TableBody>
          </Table>
        ) : (
          <p>暂无调用。未配置模型时不会产生模拟结果。</p>
        )}
        {history.hasNextPage ? (
          <Button busy={history.isFetchingNextPage} onClick={() => void history.fetchNextPage()}>
            加载更早的调用
          </Button>
        ) : null}
      </section>
      {selected ? (
        <>
          <Select
            label="选择另一个调用并排比较"
            value={compare}
            onChange={(e) => setCompare(e.target.value)}
          >
            <option value="">仅看当前调用</option>
            {calls
              .filter((c) => c.id !== selected)
              .map((c) => (
                <option key={c.id} value={c.id}>
                  {c.profile ? pinKey(c.profile) : c.task_kind} ·{" "}
                  {new Date(c.created_at).toLocaleString("zh-CN")}
                </option>
              ))}
          </Select>
          <div className={compare && compare !== selected ? "studio-two-column" : ""}>
            <ModelCallDetail key={selected} id={selected} />
            {compare && compare !== selected ? (
              <ModelCallDetail key={compare} id={compare} />
            ) : null}
          </div>
        </>
      ) : null}
    </section>
  );
}
