"use client";

import type { components } from "@accos/api-client";
import { Button, EmptyState, Input, Select, Table, TableBody, TableHead, Tabs } from "@accos/ui";
import Link from "next/link";
import { useState, type ReactNode, type SyntheticEvent } from "react";

import { InlineApiError } from "../../components/inline-api-error";
import { StateResolver } from "../../components/state-resolver";
import { useCreateArtifactMutation } from "../../lib/api/mutations";
import { useArtifactsQuery, useAssetsQuery } from "../../lib/api/queries";
import { useIdentity } from "../../providers/identity-provider";
import { useProject } from "../../providers/scope-providers";
import { canWriteProject } from "./permissions";
import { ProjectHeader } from "./project-header";
import { AssetLibrary } from "./asset-library";

type Artifact = components["schemas"]["ArtifactResponse"];
type ArtifactType = components["schemas"]["ArtifactType"];

const artifactLabels: Record<ArtifactType, string> = {
  chapter: "写作",
  character: "Characters",
  document: "文档",
  other: "其他",
  timeline: "Timeline",
  world: "World",
};

function EmptyModule({
  canWrite,
  description,
  title,
}: {
  canWrite: boolean;
  description: string;
  title: string;
}) {
  return (
    <EmptyState
      action={
        canWrite ? (
          <a className="studio-link-button" href="#create-artifact">
            创建容器
          </a>
        ) : undefined
      }
      description={description}
      title={title}
    />
  );
}

function ArtifactRows({ artifacts }: { artifacts: Artifact[] }) {
  if (artifacts.length === 0) return null;
  return (
    <Table caption="真实 Artifact 资源">
      <TableHead>
        <tr>
          <th scope="col">名称</th>
          <th scope="col">类型</th>
          <th scope="col">修订</th>
          <th scope="col">操作</th>
        </tr>
      </TableHead>
      <TableBody>
        {artifacts.map((artifact) => (
          <tr key={artifact.id}>
            <td>{artifact.label}</td>
            <td>{artifactLabels[artifact.artifact_type]}</td>
            <td>{artifact.current_revision}</td>
            <td>
              <Link href={`/projects/${artifact.project_id}/write/${artifact.id}`}>
                打开 Writing
              </Link>
            </td>
          </tr>
        ))}
      </TableBody>
    </Table>
  );
}

function ArtifactModule({
  artifacts,
  canWrite,
  description,
  emptyTitle,
}: {
  artifacts: Artifact[];
  canWrite: boolean;
  description: string;
  emptyTitle: string;
}) {
  return artifacts.length === 0 ? (
    <EmptyModule canWrite={canWrite} description={description} title={emptyTitle} />
  ) : (
    <ArtifactRows artifacts={artifacts} />
  );
}

function PanelHeading({ children, label }: { children: ReactNode; label: string }) {
  return (
    <div className="studio-section-heading">
      <div>
        <p className="studio-eyebrow">{label}</p>
        <h2>{children}</h2>
      </div>
    </div>
  );
}

export function ProjectStudio() {
  const project = useProject();
  const identity = useIdentity();
  const canWrite = canWriteProject(identity, project);
  const artifacts = useArtifactsQuery(project.workspace_id, project.id);
  const assets = useAssetsQuery(project.workspace_id, project.id);
  const createArtifact = useCreateArtifactMutation(project.workspace_id, project.id);
  const [label, setLabel] = useState("");
  const [artifactType, setArtifactType] = useState<ArtifactType>("chapter");

  if (artifacts.isPending || assets.isPending) return <StateResolver state="loading" />;
  if (artifacts.isError)
    return <StateResolver error={artifacts.error} onRetry={() => void artifacts.refetch()} />;
  if (assets.isError)
    return <StateResolver error={assets.error} onRetry={() => void assets.refetch()} />;

  function submitArtifact(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = label.trim();
    if (!trimmed) return;
    createArtifact.mutate(
      { artifact_type: artifactType, label: trimmed },
      {
        onSuccess: () => {
          setLabel("");
        },
      },
    );
  }

  const items = artifacts.data.items;
  const tabs = [
    {
      id: "info",
      label: "Project Info",
      panel: (
        <div className="studio-detail-grid">
          <dl className="studio-definition-list">
            <div>
              <dt>Project ID</dt>
              <dd>{project.id}</dd>
            </div>
            <div>
              <dt>Workspace ID</dt>
              <dd>{project.workspace_id}</dd>
            </div>
            <div>
              <dt>修订保留上限</dt>
              <dd>{project.settings.revision_retention_limit}</dd>
            </div>
            <div>
              <dt>资产保留天数</dt>
              <dd>{project.settings.asset_retention_days}</dd>
            </div>
          </dl>
        </div>
      ),
    },
    {
      id: "world",
      label: "World",
      panel: (
        <ArtifactModule
          artifacts={items.filter((item) => item.artifact_type === "world")}
          canWrite={canWrite}
          description="World Artifact 列表为空；尚未建立任何世界内容。"
          emptyTitle="World 容器为空"
        />
      ),
    },
    {
      id: "characters",
      label: "Characters",
      panel: (
        <ArtifactModule
          artifacts={items.filter((item) => item.artifact_type === "character")}
          canWrite={canWrite}
          description="Character Artifact 列表为空；尚未建立人物内容。"
          emptyTitle="Characters 容器为空"
        />
      ),
    },
    {
      id: "timeline",
      label: "Timeline",
      panel: (
        <ArtifactModule
          artifacts={items.filter((item) => item.artifact_type === "timeline")}
          canWrite={canWrite}
          description="Timeline Artifact 列表为空；尚未建立时间线内容。"
          emptyTitle="Timeline 容器为空"
        />
      ),
    },
    {
      id: "artifacts",
      label: `Artifacts · ${artifacts.data.page.total.toString()}`,
      panel:
        items.length === 0 ? (
          <EmptyModule
            canWrite={canWrite}
            description="API 返回空 Artifact 集合；Studio 不填充示例内容。"
            title="暂无 Artifact"
          />
        ) : (
          <ArtifactRows artifacts={items} />
        ),
    },
    {
      id: "assets",
      label: `Assets · ${assets.data.page.total.toString()}`,
      panel: <AssetLibrary canWrite={canWrite} />,
    },
  ] as const;

  return (
    <section className="studio-page">
      <ProjectHeader active="studio" eyebrow="Project Studio" />
      <div className="studio-summary-strip">
        <div>
          <span>Artifacts</span>
          <strong>{artifacts.data.page.total}</strong>
        </div>
        <div>
          <span>Assets</span>
          <strong>{assets.data.page.total}</strong>
        </div>
        <div>
          <span>版本</span>
          <strong>{project.version}</strong>
        </div>
      </div>
      <Tabs label="Project Studio 模块" tabs={tabs} />

      {canWrite ? (
        <section className="studio-panel" id="create-artifact">
          <PanelHeading label="Container">创建 Artifact</PanelHeading>
          <form className="studio-form-grid" onSubmit={submitArtifact}>
            <Input
              label="名称"
              maxLength={200}
              onChange={(event) => {
                setLabel(event.target.value);
              }}
              required
              value={label}
            />
            <Select
              label="类型"
              onChange={(event) => {
                setArtifactType(event.target.value as ArtifactType);
              }}
              value={artifactType}
            >
              {Object.entries(artifactLabels).map(([value, text]) => (
                <option key={value} value={value}>
                  {text}
                </option>
              ))}
            </Select>
            <Button busy={createArtifact.isPending} type="submit">
              创建空容器
            </Button>
          </form>
          {createArtifact.data ? (
            <p className="studio-success-text" role="status">
              已创建 {createArtifact.data.label}；内容仍为空。
            </p>
          ) : null}
          {createArtifact.isError ? (
            <InlineApiError error={createArtifact.error} title="Artifact 创建失败" />
          ) : null}
        </section>
      ) : (
        <p className="studio-readonly-note">当前身份仅可查看，所有 Project 写操作已隐藏。</p>
      )}
    </section>
  );
}
