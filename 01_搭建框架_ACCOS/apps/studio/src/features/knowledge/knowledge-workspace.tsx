"use client";

import type { components } from "@accos/api-client";
import { Badge, Button, EmptyState, Input, Select, Table, TableBody, TableHead } from "@accos/ui";
import { useState, type SyntheticEvent } from "react";

import { InlineApiError } from "../../components/inline-api-error";
import { StateResolver } from "../../components/state-resolver";
import {
  useCreateIngestionMutation,
  useKnowledgeSearchMutation,
  useUploadAssetMutation,
} from "../../lib/api/mutations";
import { useAssetsQuery, useIngestionRunQuery } from "../../lib/api/queries";
import { useIdentity } from "../../providers/identity-provider";
import { useProject } from "../../providers/scope-providers";
import { canWriteProject } from "../projects/permissions";
import { ProjectHeader } from "../projects/project-header";

type AssetUpload = components["schemas"]["AssetUploadRequest"];

const MAX_TECHNICAL_FILE_BYTES = 1_048_576;

function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 32_768) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 32_768));
  }
  return btoa(binary);
}

export async function fileToAssetUpload(file: File): Promise<AssetUpload> {
  if (file.size > MAX_TECHNICAL_FILE_BYTES) {
    throw new Error("技术文件不得超过 1 MiB。");
  }
  const bytes = new Uint8Array(await file.arrayBuffer());
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  const expectedSha256 = Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
  return {
    content_base64: bytesToBase64(bytes),
    expected_sha256: expectedSha256,
    filename: file.name,
    media_type: file.type || "application/octet-stream",
    source: "user_upload",
  };
}

function statusTone(status: string): "danger" | "info" | "success" | "warning" {
  if (status === "ready" || status === "indexed") return "success";
  if (status === "failed") return "danger";
  if (status === "uploaded") return "warning";
  return "info";
}

export function KnowledgeWorkspace() {
  const project = useProject();
  const identity = useIdentity();
  const canWrite = canWriteProject(identity, project);
  const assets = useAssetsQuery(project.workspace_id, project.id);
  const upload = useUploadAssetMutation(project.workspace_id, project.id);
  const ingestion = useCreateIngestionMutation(project.workspace_id, project.id);
  const search = useKnowledgeSearchMutation(project.workspace_id, project.id);
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [selectedAssetId, setSelectedAssetId] = useState("");
  const [ingestionRunId, setIngestionRunId] = useState("");
  const [query, setQuery] = useState("");
  const ingestionRun = useIngestionRunQuery(project.workspace_id, ingestionRunId);

  if (assets.isPending) return <StateResolver state="loading" />;
  if (assets.isError)
    return <StateResolver error={assets.error} onRetry={() => void assets.refetch()} />;

  async function submitUpload(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    setFileError(null);
    try {
      const body = await fileToAssetUpload(file);
      upload.mutate(body, {
        onSuccess(asset) {
          setSelectedAssetId(asset.id);
          setFile(null);
        },
      });
    } catch (error) {
      setFileError(error instanceof Error ? error.message : "无法读取文件。");
    }
  }

  function submitSearch(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = query.trim();
    if (!normalized) return;
    search.mutate({ query: normalized, top_k: 5 });
  }

  const assetId = selectedAssetId.length > 0 ? selectedAssetId : (assets.data.items[0]?.id ?? "");

  return (
    <section className="studio-page">
      <ProjectHeader active="knowledge" eyebrow="Knowledge Workspace" />

      <div className="studio-two-column">
        <section className="studio-panel">
          <div className="studio-section-heading">
            <div>
              <p className="studio-eyebrow">Asset</p>
              <h2>技术文件</h2>
            </div>
            <Badge tone="neutral">{assets.data.page.total} 个</Badge>
          </div>
          {assets.data.items.length === 0 ? (
            <EmptyState
              description="资产 API 返回空集合；尚无可摄取的来源文件。"
              title="暂无技术文件"
            />
          ) : (
            <Table caption="Knowledge 可用 Asset">
              <TableHead>
                <tr>
                  <th scope="col">文件</th>
                  <th scope="col">来源</th>
                  <th scope="col">扫描</th>
                  <th scope="col">处理</th>
                </tr>
              </TableHead>
              <TableBody>
                {assets.data.items.map((asset) => (
                  <tr key={asset.id}>
                    <td>{asset.filename}</td>
                    <td>{asset.source}</td>
                    <td>{asset.current.scan_status}</td>
                    <td>{asset.current.processing_status}</td>
                  </tr>
                ))}
              </TableBody>
            </Table>
          )}

          {canWrite ? (
            <form className="studio-form-stack" onSubmit={(event) => void submitUpload(event)}>
              <Input
                accept=".txt,.md,.json,.csv,text/plain,text/markdown,application/json,text/csv"
                description="仅用于验证骨架链路，最大 1 MiB；不要上传真实创作内容。"
                label="选择技术文件"
                onChange={(event) => {
                  setFile(event.target.files?.[0] ?? null);
                  setFileError(null);
                }}
                type="file"
                {...(fileError ? { error: fileError } : {})}
              />
              <Button busy={upload.isPending} disabled={!file} type="submit">
                上传技术文件
              </Button>
            </form>
          ) : null}
          {upload.data ? (
            <p className="studio-success-text" role="status">
              {upload.data.filename} 已由 Asset API 保存。
            </p>
          ) : null}
          {upload.isError ? <InlineApiError error={upload.error} title="上传失败" /> : null}
        </section>

        <section className="studio-panel">
          <div className="studio-section-heading">
            <div>
              <p className="studio-eyebrow">Ingestion</p>
              <h2>摄取状态</h2>
            </div>
            {ingestionRun.data ? (
              <Badge tone={statusTone(ingestionRun.data.status)}>{ingestionRun.data.status}</Badge>
            ) : null}
          </div>
          {assets.data.items.length === 0 ? (
            <p className="studio-muted">先上传一个技术文件，才能创建摄取任务。</p>
          ) : (
            <div className="studio-form-stack">
              <Select
                disabled={!canWrite}
                label="来源 Asset"
                onChange={(event) => {
                  setSelectedAssetId(event.target.value);
                }}
                value={assetId}
              >
                {assets.data.items.map((asset) => (
                  <option key={asset.id} value={asset.id}>
                    {asset.filename}
                  </option>
                ))}
              </Select>
              {canWrite ? (
                <Button
                  busy={ingestion.isPending}
                  disabled={!assetId}
                  onClick={() => {
                    ingestion.mutate(
                      { assetId },
                      {
                        onSuccess: (accepted) => {
                          setIngestionRunId(accepted.ingestion_run_id);
                        },
                      },
                    );
                  }}
                >
                  开始摄取
                </Button>
              ) : null}
            </div>
          )}
          {ingestionRun.isPending && ingestionRunId ? (
            <p className="studio-muted">正在读取摄取状态…</p>
          ) : null}
          {ingestionRun.data ? (
            <dl className="studio-definition-list studio-definition-list--compact">
              <div>
                <dt>状态</dt>
                <dd>{ingestionRun.data.status}</dd>
              </div>
              <div>
                <dt>校验</dt>
                <dd>{ingestionRun.data.verification_status}</dd>
              </div>
              <div>
                <dt>Document</dt>
                <dd>{ingestionRun.data.document_id}</dd>
              </div>
              <div>
                <dt>错误代码</dt>
                <dd>{ingestionRun.data.error_code ?? "无"}</dd>
              </div>
            </dl>
          ) : (
            <EmptyState
              description="本页尚未创建摄取任务，因此没有状态可显示。"
              title="暂无 Ingestion Run"
            />
          )}
          {ingestion.isError ? (
            <InlineApiError error={ingestion.error} title="无法创建摄取任务" />
          ) : null}
          {ingestionRun.isError ? (
            <InlineApiError error={ingestionRun.error} title="无法读取摄取状态" />
          ) : null}
        </section>
      </div>

      <section className="studio-panel">
        <div className="studio-section-heading">
          <div>
            <p className="studio-eyebrow">Retrieval</p>
            <h2>带来源检索</h2>
          </div>
        </div>
        <form className="studio-form-row" onSubmit={submitSearch}>
          <Input
            label="技术查询"
            maxLength={2000}
            onChange={(event) => {
              setQuery(event.target.value);
            }}
            placeholder="输入检索词"
            required
            value={query}
          />
          <Button busy={search.isPending} type="submit">
            检索
          </Button>
        </form>
        {search.data?.hits.length === 0 ? (
          <EmptyState
            description="检索 API 返回零条结果；没有用前端假数据填充。"
            title="没有匹配来源"
          />
        ) : null}
        {search.data && search.data.hits.length > 0 ? (
          <Table caption={`“${search.data.query}”的检索结果`}>
            <TableHead>
              <tr>
                <th scope="col">内容</th>
                <th scope="col">得分</th>
                <th scope="col">来源定位</th>
                <th scope="col">校验</th>
              </tr>
            </TableHead>
            <TableBody>
              {search.data.hits.map((hit) => (
                <tr key={hit.citation.id}>
                  <td>{hit.content}</td>
                  <td>{hit.score}</td>
                  <td className="studio-code-value">{hit.citation.locator}</td>
                  <td>{hit.citation.verification_status}</td>
                </tr>
              ))}
            </TableBody>
          </Table>
        ) : null}
        {search.isError ? <InlineApiError error={search.error} title="检索失败" /> : null}
      </section>

      {!canWrite ? (
        <p className="studio-readonly-note">当前身份仅可读取；上传和摄取按钮已隐藏。</p>
      ) : null}
    </section>
  );
}
