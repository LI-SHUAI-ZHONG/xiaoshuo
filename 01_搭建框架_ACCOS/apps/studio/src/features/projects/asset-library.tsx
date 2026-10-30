"use client";

import type { components } from "@accos/api-client";
import { Button } from "@accos/ui";
import { useQueryClient } from "@tanstack/react-query";
import { useDeferredValue, useState } from "react";
import { InlineApiError } from "../../components/inline-api-error";
import { StateResolver } from "../../components/state-resolver";
import { unwrapApiResult } from "../../lib/api/queries";
import { queryKeys } from "../../lib/api/query-keys";
import { useApiClient } from "../../providers/api-provider";
import { useProject } from "../../providers/scope-providers";
import { useAssetCatalog, useAssetHistory } from "./collection-api";

type Asset = components["schemas"]["AssetResponse"];
const fileTypes: Record<string, string> = {
  txt: "text/plain",
  md: "text/markdown",
  json: "application/json",
  pdf: "application/pdf",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  png: "image/png",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  bin: "application/octet-stream",
};

function VersionHistory({ asset }: { asset: Asset }) {
  const client = useApiClient();
  const history = useAssetHistory(asset.workspace_id, asset.project_id, asset.id);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  async function download(version: string) {
    setBusy(true);
    setError(null);
    try {
      const params = {
        path: { project_id: asset.project_id, asset_id: asset.id, version_id: version },
        header: { "X-Workspace-ID": asset.workspace_id },
      };
      const ticket = unwrapApiResult(
        await client.POST(
          "/api/v1/projects/{project_id}/assets/{asset_id}/versions/{version_id}/download-ticket",
          { params },
        ),
      );
      // A signed URL never replaces the current actor/workspace authorization.
      const claim = new URL(ticket.url, window.location.origin).searchParams.get("ticket");
      if (!claim) throw new Error("下载凭证缺失，请重试。");
      const blob = unwrapApiResult(
        await client.GET(
          "/api/v1/projects/{project_id}/assets/{asset_id}/versions/{version_id}/content",
          {
            params: { ...params, query: { ticket: claim } },
            parseAs: "blob",
          },
        ),
      );
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = asset.filename;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (cause) {
      setError(cause);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div>
      {history.isPending ? <StateResolver state="loading" /> : null}
      {history.error ? (
        <StateResolver error={history.error} onRetry={() => void history.refetch()} />
      ) : null}
      {history.data?.pages
        .flatMap((p) => p.items)
        .map((v) => (
          <div className="studio-action-row" key={v.id}>
            <span>
              版本 {v.version_number} · {v.size_bytes} 字节 ·{" "}
              {new Date(v.created_at).toLocaleString("zh-CN")}
            </span>
            <Button busy={busy} onClick={() => void download(v.id)}>
              下载版本 {v.version_number}
            </Button>
          </div>
        ))}
      {history.hasNextPage ? (
        <Button busy={history.isFetchingNextPage} onClick={() => void history.fetchNextPage()}>
          更早的资产版本
        </Button>
      ) : null}
      {error ? <InlineApiError error={error} title="下载未完成" /> : null}
    </div>
  );
}

export function AssetLibrary({ canWrite }: { canWrite: boolean }) {
  const project = useProject();
  const client = useApiClient();
  const cache = useQueryClient();
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Asset | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [inputKey, setInputKey] = useState(0);
  const [target, setTarget] = useState<Asset | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");
  const assets = useAssetCatalog(project.workspace_id, project.id, useDeferredValue(search.trim()));
  async function upload() {
    if (!file) return;
    setBusy(true);
    setError(null);
    setMessage("");
    try {
      if (file.size > 10 * 1024 * 1024) throw new Error("单个文件不能超过 10 MiB。");
      const media = fileTypes[file.name.split(".").at(-1)?.toLowerCase() ?? ""];
      if (!media) throw new Error("请选择 TXT、MD、JSON、PDF、DOCX、PNG、JPG 或 BIN 文件。");
      if (target && target.filename !== file.name) throw new Error("新版本须保持原文件名。");
      const bytes = await file.arrayBuffer();
      const digest = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), (b) =>
        b.toString(16).padStart(2, "0"),
      ).join("");
      const data = new Uint8Array(bytes);
      let binary = "";
      for (let i = 0; i < data.length; i += 8192)
        binary += String.fromCharCode(...data.subarray(i, i + 8192));
      const body = {
        filename: file.name,
        media_type: media,
        content_base64: btoa(binary),
        expected_sha256: digest,
        source: "user_upload",
      };
      const header = { "X-Workspace-ID": project.workspace_id };
      if (target)
        unwrapApiResult(
          await client.POST("/api/v1/projects/{project_id}/assets/{asset_id}/versions", {
            body,
            params: {
              path: { project_id: project.id, asset_id: target.id },
              header: { ...header, "If-Match": `"${target.version}"` },
            },
          }),
        );
      else
        unwrapApiResult(
          await client.POST("/api/v1/projects/{project_id}/assets", {
            body,
            params: { path: { project_id: project.id }, header },
          }),
        );
      setFile(null);
      setInputKey((k) => k + 1);
      setTarget(null);
      setMessage("文件已上传，可查看版本和下载。");
      await cache.invalidateQueries({
        queryKey: queryKeys.assets(project.workspace_id, project.id),
      });
    } catch (cause) {
      setError(cause);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="studio-panel">
      <h2>资产与版本</h2>
      <label>
        搜索文件
        <input value={search} maxLength={200} onChange={(e) => setSearch(e.target.value)} />
      </label>
      {assets.isPending ? <StateResolver state="loading" /> : null}
      {assets.error ? (
        <StateResolver error={assets.error} onRetry={() => void assets.refetch()} />
      ) : null}
      {assets.data?.pages
        .flatMap((p) => p.items)
        .map((asset) => (
          <div key={asset.id} className="studio-action-row">
            <span>
              {asset.filename} · 版本 {asset.current_version} · {asset.current.size_bytes} 字节
            </span>
            <Button onClick={() => setSelected(asset)}>查看历史与下载</Button>
            {canWrite && asset.status === "active" ? (
              <Button
                disabled={busy}
                onClick={() => {
                  setTarget(asset);
                  setFile(null);
                  setInputKey((k) => k + 1);
                }}
              >
                上传新版本
              </Button>
            ) : null}
          </div>
        ))}
      {assets.data?.pages[0]?.items.length === 0 ? <p>没有符合条件的文件。</p> : null}
      {assets.hasNextPage ? (
        <Button busy={assets.isFetchingNextPage} onClick={() => void assets.fetchNextPage()}>
          更多文件
        </Button>
      ) : null}
      {selected ? (
        <section>
          <h3>{selected.filename} 的版本历史</h3>
          <VersionHistory key={selected.id} asset={selected} />
          <Button onClick={() => setSelected(null)}>关闭历史</Button>
        </section>
      ) : null}
      {canWrite ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void upload();
          }}
        >
          <p>{target ? `为「${target.filename}」上传新版本` : "上传文件（最大 10 MiB）"}</p>
          <label>
            选择文件
            <input
              key={inputKey}
              type="file"
              disabled={busy}
              accept=".txt,.md,.json,.pdf,.docx,.png,.jpg,.jpeg,.bin"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>
          <Button type="submit" disabled={!file} busy={busy}>
            上传文件
          </Button>
          {target ? (
            <Button disabled={busy} onClick={() => setTarget(null)}>
              改为独立文件
            </Button>
          ) : null}
        </form>
      ) : null}
      {message ? <p role="status">{message}</p> : null}
      {error ? <InlineApiError error={error} title="上传未完成，所选文件仍保留" /> : null}
    </section>
  );
}
