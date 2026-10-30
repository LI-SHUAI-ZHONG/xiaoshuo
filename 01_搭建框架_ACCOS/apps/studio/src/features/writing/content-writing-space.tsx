"use client";

import type { components } from "@accos/api-client";
import { Button } from "@accos/ui";
import { useEffect, useState } from "react";
import { InlineApiError } from "../../components/inline-api-error";
import { StateResolver } from "../../components/state-resolver";
import { useArtifactQuery } from "../../lib/api/queries";
import { asApiProblem } from "../../lib/api/errors";
import { useIdentity } from "../../providers/identity-provider";
import { useProject } from "../../providers/scope-providers";
import { canWriteProject } from "../projects/permissions";
import { ProjectHeader } from "../projects/project-header";
import { ContentEditor } from "./editor";
import { useWritingCopy, type Choices } from "./use-writing-copy";

type Revision = components["schemas"]["ContentRevision"];
type Branch = components["schemas"]["Branch"];
type Merge = components["schemas"]["MergeResult"];

function blockText(block: components["schemas"]["EditorBlock"] | null | undefined) {
  return block
    ? (block.content ?? []).map((part) => (part.type === "text" ? part.text : "\n")).join("")
    : "（此段已删除）";
}
function downloadDraft(value: unknown) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = "本机正文草稿.json";
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function ConflictChoices({
  result,
  choices,
  setChoices,
}: {
  result: Merge;
  choices: Choices;
  setChoices: (c: Choices) => void;
}) {
  return (
    <div>
      {result.conflicts.map((item) => (
        <fieldset key={item.block_id} className="studio-panel">
          <legend>
            {item.reason === "incompatible_order" ? "段落顺序冲突" : "同一段落有不同修改"}
          </legend>
          <div className="studio-detail-grid">
            <div>
              <strong>服务器／当前分支</strong>
              <pre className="content-preview">{blockText(item.ours)}</pre>
            </div>
            <div>
              <strong>本机／待合并分支</strong>
              <pre className="content-preview">{blockText(item.theirs)}</pre>
            </div>
          </div>
          <label>
            保留哪一方
            <select
              value={choices[item.block_id] ?? ""}
              onChange={(e) =>
                setChoices({ ...choices, [item.block_id]: e.target.value as "ours" | "theirs" })
              }
            >
              <option value="" disabled>
                请选择
              </option>
              <option value="ours">服务器／当前分支</option>
              <option value="theirs">本机／待合并分支</option>
            </select>
          </label>
        </fieldset>
      ))}
    </div>
  );
}

function WritingDocument({
  artifactId,
  selectedBranch,
  onBranch,
}: {
  artifactId: string;
  selectedBranch?: string;
  onBranch: (branch: string) => void;
}) {
  const project = useProject();
  const identity = useIdentity();
  const canWrite = canWriteProject(identity, project);
  const writer = useWritingCopy(
    identity.actor_id,
    project.workspace_id,
    project.id,
    artifactId,
    selectedBranch,
  );
  const { api, copy } = writer;
  const [history, setHistory] = useState<Revision[]>([]);
  const [historyCursor, setHistoryCursor] = useState<string | null>(null);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [branchCursor, setBranchCursor] = useState<string | null>(null);
  const [branchName, setBranchName] = useState("");
  const [preview, setPreview] = useState<components["schemas"]["RevisionContent"] | null>(null);
  const [merge, setMerge] = useState<{
    result: Merge;
    source: string;
    target: string;
    version: number;
    epoch: number;
  } | null>(null);
  const [choices, setChoices] = useState<Choices>({});
  const [pending, setPending] = useState(false);
  useEffect(() => {
    let active = true;
    void Promise.all([api.history(), api.branches()])
      .then(([revisions, available]) => {
        if (active) {
          setHistory(revisions.items);
          setHistoryCursor(revisions.next_cursor ?? null);
          setBranches(available.items);
          setBranchCursor(available.next_cursor ?? null);
        }
      })
      .catch(writer.setError);
    return () => {
      active = false;
    };
  }, [api, copy?.revision?.id, writer.setError]);
  async function run(action: () => Promise<void>) {
    setPending(true);
    writer.setError(null);
    try {
      await action();
    } catch (cause) {
      writer.setError(cause);
    } finally {
      setPending(false);
    }
  }
  if (!copy || !writer.document)
    return (
      <>
        {writer.error ? (
          <StateResolver error={writer.error} onRetry={() => void run(writer.load)} />
        ) : (
          <StateResolver state="loading" />
        )}
        {writer.recoveries.length ? (
          <section className="studio-panel">
            <h2>本机未同步稿</h2>
            <p>{writer.message}</p>
            {writer.recoveries.map((draft) => (
              <div key={draft.key} className="studio-action-row">
                <span>
                  {new Date(draft.updatedAt).toLocaleString("zh-CN")} · 基线 {draft.version}
                </span>
                <Button
                  disabled={!canWrite || pending}
                  onClick={() => void run(() => writer.recover(draft))}
                >
                  恢复此本机稿
                </Button>
                <Button onClick={() => downloadDraft(draft.document)}>下载此本机稿</Button>
              </div>
            ))}
          </section>
        ) : null}
      </>
    );
  const loaded = copy;
  const disabled =
    !canWrite || copy.branch.archived || copy.branch.editing_mode !== "solo" || pending;
  return (
    <>
      <section className="studio-panel">
        <div className="studio-action-row">
          <label>
            当前分支
            <select
              aria-label="当前分支"
              value={copy.branch.id}
              disabled={!writer.canChangeBranch || pending}
              onChange={(e) => onBranch(e.target.value)}
            >
              {!branches.some((b) => b.id === copy.branch.id) ? (
                <option value={copy.branch.id}>{copy.branch.name}</option>
              ) : null}
              {branches.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                  {b.archived ? "（已归档）" : ""}
                </option>
              ))}
            </select>
          </label>
          {branchCursor ? (
            <Button
              onClick={() =>
                void run(async () => {
                  const page = await api.branches(branchCursor);
                  setBranches((old) => [...old, ...page.items]);
                  setBranchCursor(page.next_cursor ?? null);
                })
              }
            >
              更多分支
            </Button>
          ) : null}
          <span role="status" aria-live="polite">
            {writer.message}
          </span>
        </div>
        {writer.recoveries.length ? (
          <details open>
            <summary>发现 {writer.recoveries.length} 份本机未同步稿</summary>
            <p>恢复后会按保存时的基线核对服务器版本，其他窗口的稿件会继续保留。</p>
            {writer.recoveries.map((draft) => (
              <div key={draft.key} className="studio-action-row">
                <span>
                  {new Date(draft.updatedAt).toLocaleString("zh-CN")} · 基线 {draft.version}
                </span>
                <Button
                  disabled={disabled || writer.dirty || writer.busy}
                  onClick={() => void run(() => writer.recover(draft))}
                >
                  恢复此本机稿
                </Button>
                <Button onClick={() => downloadDraft(draft.document)}>下载此本机稿</Button>
              </div>
            ))}
          </details>
        ) : null}
        <ContentEditor
          value={writer.document}
          disabled={disabled || writer.resolving || !!writer.conflict}
          onChange={writer.change}
          onComposing={writer.onComposing}
        />
        <div className="studio-action-row">
          <Button
            disabled={disabled || !writer.dirty || !!writer.conflict}
            busy={writer.busy}
            onClick={() => void writer.retry()}
          >
            保存正文
          </Button>
          <Button onClick={() => downloadDraft(writer.document)}>下载本机草稿</Button>
          <span>
            服务器版本 {copy.branch.version} · {writer.dirty ? "有未同步输入" : "无未同步输入"}
          </span>
        </div>
        {writer.error ? (
          <InlineApiError error={writer.error} title="正文操作未完成，本机稿已保留" />
        ) : null}
      </section>
      {writer.conflict ? (
        <section className="studio-panel">
          <h2>合并本机与服务器稿件</h2>
          <p>
            {writer.conflict.result.conflicts.length
              ? "选择冲突段落的保留内容。"
              : "修改位于不同段落，可以合并。"}
          </p>
          <ConflictChoices
            result={writer.conflict.result}
            choices={choices}
            setChoices={setChoices}
          />
          <Button
            busy={pending}
            onClick={() =>
              void run(async () => {
                await writer.reconcile(choices);
                setChoices({});
              })
            }
          >
            确认合并并继续保存
          </Button>
        </section>
      ) : null}
      {canWrite ? (
        <section className="studio-panel">
          <h2>分支试写</h2>
          <div className="studio-action-row">
            <label>
              新分支名称
              <input
                value={branchName}
                maxLength={100}
                onChange={(e) => setBranchName(e.target.value)}
              />
            </label>
            <Button
              disabled={!branchName.trim() || !writer.canChangeBranch}
              busy={pending}
              onClick={() =>
                void run(async () => {
                  const value = await api.createBranch(
                    branchName.trim(),
                    loaded.branch.head_revision_id ?? null,
                    crypto.randomUUID(),
                  );
                  onBranch(value.id);
                })
              }
            >
              从当前版本创建分支
            </Button>
          </div>
          <p>先同步当前输入，再切换或合并分支。</p>
          {branches
            .filter((b) => b.name !== "主稿")
            .map((b) => (
              <Button
                key={`archive-${b.id}`}
                disabled={!writer.canChangeBranch || pending}
                onClick={() =>
                  void run(async () => {
                    await api.archiveBranch(b.id, b.version, !b.archived);
                    const page = await api.branches();
                    setBranches(page.items);
                    setBranchCursor(page.next_cursor ?? null);
                    if (b.id === loaded.branch.id) await writer.load();
                  })
                }
              >
                {b.archived ? "恢复" : "归档"}分支「{b.name}」
              </Button>
            ))}
          {branches
            .filter((b) => b.id !== loaded.branch.id && b.head_revision_id)
            .map((b) => (
              <Button
                key={b.id}
                disabled={!writer.canChangeBranch || !loaded.branch.head_revision_id || pending}
                onClick={() =>
                  void run(async () => {
                    const source = b.head_revision_id!,
                      target = loaded.branch.head_revision_id!;
                    setChoices({});
                    setMerge({
                      result: await api.diff(target, source),
                      source,
                      target,
                      version: loaded.branch.version,
                      epoch: loaded.branch.document_epoch,
                    });
                  })
                }
              >
                比较并合并「{b.name}」
              </Button>
            ))}
          {merge ? (
            <div>
              <h3>合并预览</h3>
              <ConflictChoices result={merge.result} choices={choices} setChoices={setChoices} />
              {merge.result.order_changed ? <p>两个版本的段落顺序不同。</p> : null}
              {(merge.result.differences ?? []).map((item) => (
                <div key={item.block_id} className="studio-detail-grid">
                  <pre className="content-preview">当前稿：{blockText(item.ours)}</pre>
                  <pre className="content-preview">分支稿：{blockText(item.theirs)}</pre>
                </div>
              ))}
              <pre className="content-preview">
                {merge.result.document.content.map(blockText).join("\n")}
              </pre>
              <Button
                disabled={!writer.canChangeBranch}
                busy={pending}
                onClick={() =>
                  void run(async () => {
                    await api.merge(merge.version, {
                      branch_id: loaded.branch.id,
                      base_revision_id: merge.target,
                      source_revision_id: merge.source,
                      document_epoch: merge.epoch,
                      client_change_id: crypto.randomUUID(),
                      resolutions: choices,
                    });
                    setMerge(null);
                    setChoices({});
                    await writer.load();
                  })
                }
              >
                确认生成合并版本
              </Button>
              <Button onClick={() => setMerge(null)}>取消</Button>
            </div>
          ) : null}
        </section>
      ) : null}
      <section className="studio-panel">
        <h2>修订历史</h2>
        {history.length ? (
          <table>
            <thead>
              <tr>
                <th>版本</th>
                <th>操作</th>
                <th>保存时间</th>
                <th>查看／恢复</th>
              </tr>
            </thead>
            <tbody>
              {history.map((revision) => (
                <tr key={revision.id}>
                  <td>{revision.revision_number}</td>
                  <td>{revision.operation}</td>
                  <td>{new Date(revision.created_at).toLocaleString("zh-CN")}</td>
                  <td>
                    <Button
                      onClick={() =>
                        void run(async () => {
                          setPreview(await api.content(revision.id));
                        })
                      }
                    >
                      查看全文
                    </Button>
                    {canWrite ? (
                      <Button
                        disabled={
                          !writer.canChangeBranch ||
                          revision.content_status !== "available" ||
                          pending
                        }
                        onClick={() =>
                          void run(async () => {
                            await api.restore(revision.id, loaded.branch.version, {
                              branch_id: loaded.branch.id,
                              base_revision_id: loaded.branch.head_revision_id ?? null,
                              document_epoch: loaded.branch.document_epoch,
                              client_change_id: crypto.randomUUID(),
                            });
                            await writer.load();
                          })
                        }
                      >
                        恢复为新版本
                      </Button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>尚无修订，输入后会自动保存。</p>
        )}
        {historyCursor ? (
          <Button
            busy={pending}
            onClick={() =>
              void run(async () => {
                const page = await api.history(historyCursor);
                setHistory((old) => [...old, ...page.items]);
                setHistoryCursor(page.next_cursor ?? null);
              })
            }
          >
            更早的修订
          </Button>
        ) : null}
        {preview ? (
          <div>
            <h3>版本 {preview.revision.revision_number}</h3>
            <pre className="content-preview">
              {preview.text ?? "旧记录没有可读取的正文；原始引用和哈希仍保留。"}
            </pre>
            <p>
              父版本数：{preview.revision.parents.length} · 哈希：
              {preview.revision.content_hash ?? "无"}
            </p>
            <Button onClick={() => setPreview(null)}>关闭预览</Button>
          </div>
        ) : null}
      </section>
    </>
  );
}

export function WritingSpace({ artifactId }: { artifactId: string }) {
  const project = useProject();
  const identity = useIdentity();
  const artifact = useArtifactQuery(project.workspace_id, project.id, artifactId);
  const [branch, setBranch] = useState<string>();
  if (artifact.isPending) return <StateResolver state="loading" />;
  if (!artifact.data || (artifact.isError && asApiProblem(artifact.error).kind !== "offline"))
    return <StateResolver error={artifact.error} onRetry={() => void artifact.refetch()} />;
  return (
    <section className="studio-page studio-page--wide">
      <ProjectHeader
        active="writing"
        artifactId={artifactId}
        eyebrow="写作"
        title={artifact.data.label}
      />
      <WritingDocument
        key={`${identity.actor_id}:${project.workspace_id}:${project.id}:${artifactId}:${branch ?? "main"}`}
        artifactId={artifactId}
        {...(branch ? { selectedBranch: branch } : {})}
        onBranch={setBranch}
      />
    </section>
  );
}
