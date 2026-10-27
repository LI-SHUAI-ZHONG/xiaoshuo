"use client";

import { Button, Input, Select } from "@accos/ui";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { StateResolver } from "../../components/state-resolver";
import { useIdentity } from "../../providers/identity-provider";
import { pinKey, useModelApi, type Prompt } from "./model-api";
import {
  ModelNavigation,
  TextArea,
  objectJson,
  pretty,
  useAction,
  useModelOwner,
} from "./model-common";

const newer = (a: string, b: string) => {
  const first = a.split(".").map(Number),
    second = b.split(".").map(Number);
  for (let i = 0; i < 3; i++) {
    const difference = (first[i] ?? 0) - (second[i] ?? 0);
    if (difference) return difference;
  }
  return 0;
};

export function PromptWorkspace() {
  const identity = useIdentity();
  const owner = useModelOwner();
  const api = useModelApi(identity.workspace_id);
  const client = useQueryClient();
  const key = ["prompt-releases", identity.actor_id, identity.workspace_id];
  const query = useQuery({ queryKey: key, queryFn: api.prompts });
  const [draft, setDraft] = useState<Prompt | null>(null);
  const [expected, setExpected] = useState("0");
  const [variablesSchema, setVariablesSchema] = useState("{}");
  const [outputSchema, setOutputSchema] = useState("{}");
  const [variables, setVariables] = useState(
    pretty({
      task: "",
      context: "[]",
      constraints: "",
      available_tools: [],
      available_workflows: [],
    }),
  );
  const [preview, setPreview] = useState("");
  const action = useAction();
  if (query.isPending) return <StateResolver state="loading" />;
  if (query.isError)
    return <StateResolver error={query.error} onRetry={() => void query.refetch()} />;
  function edit(prompt: Prompt, create = false) {
    const latest =
      query
        .data!.filter((p) => p.id === prompt.id)
        .map((p) => p.version)
        .sort(newer)
        .at(-1) ?? prompt.version;
    const pieces = latest.split(".");
    pieces[2] = String(Number(pieces[2]) + 1);
    setDraft({
      ...prompt,
      id: create ? "" : prompt.id,
      version: create ? "1.0.0" : pieces.join("."),
      checksum: "",
    });
    setExpected(create ? "0" : latest);
    setVariablesSchema(pretty(prompt.variables_schema));
    setOutputSchema(pretty(prompt.output_schema));
    setPreview("");
  }
  function current(): Prompt {
    if (!draft) throw new Error("请先选择一个模板。");
    return {
      ...draft,
      checksum: "",
      variables_schema: objectJson(variablesSchema),
      output_schema: objectJson(outputSchema),
    };
  }
  return (
    <section className="studio-page studio-page--wide">
      <header className="studio-page__header">
        <h1>Prompt 版本与预览</h1>
        <p>系统附带公共任务和 Director 模板；自定义内容以新版本发布，已排队任务继续使用原版本。</p>
      </header>
      <ModelNavigation />
      {action.notice}
      <section className="studio-panel">
        <h2>已发布版本</h2>
        <Select
          label="选择模板以查看或编辑"
          value=""
          onChange={(e) => {
            const prompt = query.data.find((p) => pinKey(p) === e.target.value);
            if (prompt) edit(prompt);
          }}
        >
          <option value="">请选择模板</option>
          {query.data.map((p) => (
            <option value={pinKey(p)} key={pinKey(p)}>
              {p.title} · {pinKey(p)}
            </option>
          ))}
        </Select>
        <Button
          variant="secondary"
          disabled={!owner || query.data.length === 0}
          onClick={() => {
            const prompt = query.data.find((p) => p.id === "agent.task") ?? query.data[0];
            if (prompt) edit(prompt, true);
          }}
        >
          基于公共协议新建模板
        </Button>
        <details>
          <summary>版本、校验和与适用任务</summary>
          <ul>
            {query.data.map((p) => (
              <li key={pinKey(p)}>
                <strong>{pinKey(p)}</strong>
                <p>
                  {p.title} · {p.allowed_tasks.join("、")}
                </p>
                <code className="studio-code-value">{p.checksum}</code>
              </li>
            ))}
          </ul>
        </details>
      </section>
      {draft ? (
        <form
          className="studio-panel studio-form-stack"
          onSubmit={(event) => {
            event.preventDefault();
            void action.run(async () => {
              const result = await api.publishPrompt(current(), expected);
              await client.invalidateQueries({ queryKey: key });
              setExpected(result.version);
              const parts = result.version.split(".");
              parts[2] = String(Number(parts[2]) + 1);
              setDraft({ ...result, version: parts.join("."), checksum: "" });
            });
          }}
        >
          <h2>编辑新版本</h2>
          <fieldset className="model-fieldset studio-form-stack" disabled={!owner || action.busy}>
            <div className="studio-form-grid">
              <Input
                label="模板 ID"
                required
                readOnly={expected !== "0"}
                value={draft.id}
                onChange={(e) => setDraft({ ...draft, id: e.target.value })}
              />
              <Input
                label="标题"
                required
                value={draft.title}
                onChange={(e) => setDraft({ ...draft, title: e.target.value })}
              />
              <Input
                label="发布版本（主.次.补丁）"
                required
                pattern="[0-9]+\.[0-9]+\.[0-9]+"
                value={draft.version}
                onChange={(e) => setDraft({ ...draft, version: e.target.value })}
              />
            </div>
            <TextArea
              label="系统模板"
              rows={10}
              minLength={100}
              maxLength={40000}
              required
              value={draft.system_template}
              onChange={(e) => setDraft({ ...draft, system_template: e.target.value })}
            />
            <TextArea
              label="用户模板（变量使用双花括号）"
              rows={7}
              required
              value={draft.user_template}
              onChange={(e) => setDraft({ ...draft, user_template: e.target.value })}
            />
            <div className="studio-form-grid">
              <Input
                label="适用任务（逗号分隔）"
                required
                value={draft.allowed_tasks.join(",")}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    allowed_tasks: e.target.value
                      .split(",")
                      .map((s) => s.trim())
                      .filter(Boolean),
                  })
                }
              />
              <Input
                label="允许工具（逗号分隔；空为禁用）"
                value={draft.allowed_tools?.join(",") ?? ""}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    allowed_tools: e.target.value
                      .split(",")
                      .map((s) => s.trim())
                      .filter(Boolean),
                  })
                }
              />
            </div>
            <div className="studio-two-column">
              <TextArea
                label="变量 JSON Schema"
                rows={14}
                required
                value={variablesSchema}
                onChange={(e) => setVariablesSchema(e.target.value)}
              />
              <TextArea
                label="输出 JSON Schema"
                rows={14}
                required
                value={outputSchema}
                onChange={(e) => setOutputSchema(e.target.value)}
              />
            </div>
            <Button type="submit">发布不可变版本</Button>
          </fieldset>
          <h2>变量预览</h2>
          <p>预览只校验并渲染模板，不调用模型，也不保存为任务。</p>
          <TextArea
            label="预览变量 JSON"
            rows={8}
            value={variables}
            onChange={(e) => setVariables(e.target.value)}
          />
          <Button
            busy={action.busy}
            variant="secondary"
            onClick={() =>
              void action.run(async () => {
                const prompt = current();
                const rendered = await api.preview(
                  prompt,
                  prompt.allowed_tasks[0] ?? "",
                  objectJson(variables),
                );
                setPreview(rendered.map((m) => m.role + "\n" + (m.text ?? "")).join("\n\n"));
              }, "预览已更新。")
            }
          >
            校验并预览
          </Button>
          {preview ? <pre className="model-content">{preview}</pre> : null}
        </form>
      ) : (
        <p>选择已有模板后查看正文、变量和输出协议。</p>
      )}
    </section>
  );
}
