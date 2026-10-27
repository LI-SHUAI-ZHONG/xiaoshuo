"use client";

import { Button, Input, Select, Table, TableBody, TableHead } from "@accos/ui";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { StateResolver } from "../../components/state-resolver";
import { useIdentity } from "../../providers/identity-provider";
import { useProject } from "../../providers/scope-providers";
import { StatusBadge } from "../monitoring/status-badge";
import { ContentPicker } from "./content-picker";
import { money, pinKey, terminalCall, useModelApi, type ContentRef } from "./model-api";
import { pretty, useAction, useModelOwner } from "./model-common";

function readableContent(text: string, kind: string): string {
  if (kind === "partial") return text;
  try {
    const document = JSON.parse(text) as Record<string, unknown>;
    if (kind === "output" && typeof document.text === "string")
      return document.text || pretty(document.embeddings ?? document.tool_calls ?? document);
    // Provider continuation payloads are transport data, not an explanation of reasoning.
    return JSON.stringify(
      document,
      (key, value: unknown) =>
        ["provider_items", "continuation"].includes(key) ? undefined : value,
      2,
    );
  } catch {
    return text;
  }
}

export function ModelCallDetail({ id }: { id: string }) {
  const identity = useIdentity();
  const project = useProject();
  const owner = useModelOwner();
  const api = useModelApi(identity.workspace_id, project.id);
  const cache = useQueryClient();
  const key = ["model-call", identity.actor_id, identity.workspace_id, project.id, id];
  const call = useQuery({
    queryKey: key,
    queryFn: () => api.call(id),
    refetchInterval: (q) => (q.state.data && terminalCall(q.state.data.status) ? false : 1000),
  });
  const attempts = useQuery({
    queryKey: [...key, "attempts", call.data?.sequence],
    queryFn: () => api.attempts(id),
    enabled: Boolean(call.data),
  });
  const [kind, setKind] = useState<"input" | "output" | "partial">("output");
  const [reservation, setReservation] = useState("");
  const [cost, setCost] = useState("");
  const [input, setInput] = useState("");
  const [output, setOutput] = useState("");
  const [cached, setCached] = useState("0");
  const [evidence, setEvidence] = useState<ContentRef[]>([]);
  const [score, setScore] = useState("3");
  const action = useAction();
  const available =
    kind === "input" ||
    (kind === "output" ? Boolean(call.data?.output_ref) : Boolean(call.data?.partial_ref));
  const content = useQuery({
    queryKey: [...key, "content", kind, call.data?.sequence],
    queryFn: () => api.content(id, kind),
    enabled: Boolean(call.data) && available,
  });
  if (call.isPending) return <StateResolver state="loading" />;
  if (call.isError) return <StateResolver error={call.error} onRetry={() => void call.refetch()} />;
  const value = call.data;
  return (
    <article className="studio-panel studio-form-stack">
      <div className="studio-panel__heading">
        <h2>调用详情</h2>
        <StatusBadge status={value.status} />
      </div>
      <p className="studio-code-value">{id}</p>
      <p>
        策略 {pinKey(value.policy)} · 模型 {value.profile ? pinKey(value.profile) : "尚未选择"} ·
        Prompt {value.prompt ? pinKey(value.prompt) : "直接输入"}
      </p>
      <p>
        耗时 {value.duration_ms == null ? "待完成" : value.duration_ms + " ms"} · Token{" "}
        {value.usage ? value.usage.input_tokens + value.usage.output_tokens : "未知"} · 费用{" "}
        {money(value.cost_micro_usd)} · 计费 {value.billing_status}
      </p>
      {value.error_code ? <p role="status">{value.error_code}</p> : null}
      <p>
        输入资产：{value.input_ref.sha256}。已落盘输出和暂存内容分别保留；候选结果尚未被作者接受。
      </p>
      {identity.permissions.includes("model:run") &&
      project.status === "active" &&
      !terminalCall(value.status) ? (
        <Button
          busy={action.busy}
          disabled={value.cancel_requested}
          onClick={() =>
            void action.run(async () => {
              await api.cancel(id);
              await cache.invalidateQueries({ queryKey: key });
            }, "已请求取消；若已向供应商发送请求，费用可能仍需对账。")
          }
        >
          {value.cancel_requested ? "正在取消" : "取消此调用"}
        </Button>
      ) : null}
      {action.notice}
      <Select
        label="查看内容"
        value={kind}
        onChange={(e) => setKind(e.target.value as typeof kind)}
      >
        <option value="output">完整返回</option>
        <option value="partial">流式暂存</option>
        <option value="input">冻结输入</option>
      </Select>
      {!available ? (
        <p>此内容尚未产生。</p>
      ) : content.isPending ? (
        <StateResolver state="loading" />
      ) : content.isError ? (
        <StateResolver error={content.error} onRetry={() => void content.refetch()} />
      ) : (
        <pre className="model-content">{readableContent(content.data.text, kind)}</pre>
      )}
      <h3>逐次尝试与费用</h3>
      {attempts.isError ? (
        <StateResolver error={attempts.error} onRetry={() => void attempts.refetch()} />
      ) : (
        <Table caption="预算尝试账本">
          <TableHead>
            <tr>
              <th>尝试 / 模型</th>
              <th>价格版本</th>
              <th>状态</th>
              <th>预留 / 结算</th>
              <th>错误</th>
            </tr>
          </TableHead>
          <TableBody>
            {attempts.data?.map((r) => (
              <tr key={r.id}>
                <td>
                  {r.attempt} · {r.profile_id}@{r.profile_version}
                </td>
                <td>{r.price_version}</td>
                <td>{r.status}</td>
                <td>
                  {money(r.reserved_micro_usd)} / {money(r.cost_micro_usd)}
                </td>
                <td>{r.error_code ?? "—"}</td>
              </tr>
            ))}
          </TableBody>
        </Table>
      )}
      {owner && attempts.data?.some((r) => r.status === "unknown") ? (
        <form
          className="studio-form-stack"
          onSubmit={(e) => {
            e.preventDefault();
            void action.run(async () => {
              const ref = evidence[0];
              if (!ref) throw new Error("请选择已上传的账单或用量凭据。");
              await api.reconcile(id, reservation, {
                usage: {
                  input_tokens: Number(input),
                  output_tokens: Number(output),
                  cached_input_tokens: Number(cached),
                },
                cost_micro_usd: Number(cost),
                evidence_ref: ref,
              });
              await cache.invalidateQueries({ queryKey: key });
            }, "已记录对账凭据并更新费用；生成结果的状态保持原状。");
          }}
        >
          <h3>人工对账</h3>
          <Select
            label="待对账尝试"
            required
            value={reservation}
            onChange={(e) => setReservation(e.target.value)}
          >
            <option value="">选择尝试</option>
            {attempts.data
              .filter((r) => r.status === "unknown")
              .map((r) => (
                <option key={r.id} value={r.id}>
                  第 {r.attempt} 次 · {r.profile_id}
                </option>
              ))}
          </Select>
          <div className="studio-form-grid">
            <Input
              label="实际输入 Token"
              type="number"
              min={0}
              required
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <Input
              label="实际输出 Token"
              type="number"
              min={0}
              required
              value={output}
              onChange={(e) => setOutput(e.target.value)}
            />
            <Input
              label="其中缓存输入 Token"
              type="number"
              min={0}
              required
              value={cached}
              onChange={(e) => setCached(e.target.value)}
            />
            <Input
              label="实际费用（微美元）"
              type="number"
              min={0}
              required
              value={cost}
              onChange={(e) => setCost(e.target.value)}
            />
          </div>
          <ContentPicker
            workspace={identity.workspace_id}
            project={project.id}
            value={evidence}
            onChange={setEvidence}
            single
            textOnly={false}
          />
          <Button busy={action.busy} type="submit" disabled={!reservation || !evidence.length}>
            保存有凭据的对账
          </Button>
        </form>
      ) : null}
      {value.output_ref && identity.permissions.includes("project:write") ? (
        <div className="studio-form-row">
          <Select
            label="人工输出评价（0–4）"
            value={score}
            onChange={(e) => setScore(e.target.value)}
          >
            {[0, 1, 2, 3, 4].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </Select>
          <Button
            busy={action.busy}
            variant="secondary"
            onClick={() =>
              void action.run(async () => {
                await api.feedback(id, Number(score));
              }, "人工评价已保存至项目反馈，引用此调用。")
            }
          >
            保存评价
          </Button>
        </div>
      ) : null}
    </article>
  );
}
