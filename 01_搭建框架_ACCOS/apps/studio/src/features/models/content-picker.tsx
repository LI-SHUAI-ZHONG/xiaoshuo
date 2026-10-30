"use client";

import { Button, Input } from "@accos/ui";
import { useDeferredValue, useState } from "react";
import { StateResolver } from "../../components/state-resolver";
import { useAssetCatalog } from "../projects/collection-api";
import type { ContentRef } from "./model-api";

export function ContentPicker({
  workspace,
  project,
  value,
  onChange,
  single = false,
  textOnly = true,
}: {
  workspace: string;
  project: string;
  value: ContentRef[];
  onChange: (items: ContentRef[]) => void;
  single?: boolean;
  textOnly?: boolean;
}) {
  const [search, setSearch] = useState("");
  const assets = useAssetCatalog(workspace, project, useDeferredValue(search));
  return (
    <details>
      <summary>选择已上传的资产版本（已选 {value.length}）</summary>
      <p>选中时固定资产版本。需要上传新资料时，可在项目首页的资产列表操作。</p>
      {value.map((ref) => (
        <p key={ref.asset_version_id}>
          <code>
            {ref.asset_id} / {ref.sha256.slice(0, 12)}
          </code>{" "}
          <Button
            variant="secondary"
            onClick={() =>
              onChange(value.filter((r) => r.asset_version_id !== ref.asset_version_id))
            }
          >
            移除引用
          </Button>
        </p>
      ))}
      <Input label="搜索资产名称" value={search} onChange={(e) => setSearch(e.target.value)} />
      {assets.isPending ? <StateResolver state="loading" /> : null}
      {assets.isError ? (
        <StateResolver error={assets.error} onRetry={() => void assets.refetch()} />
      ) : null}
      {assets.data?.pages
        .flatMap((p) => p.items)
        .filter(
          (asset) =>
            asset.status === "active" &&
            (!textOnly ||
              ["text/plain", "text/markdown", "application/json"].includes(
                asset.current.media_type,
              )),
        )
        .map((asset) => (
          <div className="studio-action-row" key={asset.id}>
            <span>
              {asset.filename} · v{asset.current_version} · {asset.current.size_bytes} 字节
            </span>
            <Button
              variant="secondary"
              disabled={
                value.some((r) => r.asset_version_id === asset.current.id) ||
                (!single && value.length >= 32)
              }
              onClick={() => {
                const ref: ContentRef = {
                  asset_id: asset.id,
                  asset_version_id: asset.current.id,
                  sha256: asset.current.content_hash,
                  media_type: asset.current.media_type,
                  byte_length: asset.current.size_bytes,
                };
                onChange(single ? [ref] : [...value, ref]);
              }}
            >
              选择此版本
            </Button>
          </div>
        ))}
      {assets.hasNextPage ? (
        <Button busy={assets.isFetchingNextPage} onClick={() => void assets.fetchNextPage()}>
          更多资产
        </Button>
      ) : null}
    </details>
  );
}
