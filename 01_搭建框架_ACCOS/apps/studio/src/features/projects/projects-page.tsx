"use client";

import { Badge, Button, EmptyState, Table, TableBody, TableHead } from "@accos/ui";
import Link from "next/link";
import { useDeferredValue, useState } from "react";

import { StateResolver } from "../../components/state-resolver";
import { useProjectCatalog } from "./collection-api";
import { ProjectActions } from "./project-actions";
import { useIdentity } from "../../providers/identity-provider";
import { canWriteProjects } from "./permissions";
import { ProjectCreatePanel } from "./project-create-panel";

export function ProjectsPage() {
  const identity = useIdentity();
  const [search, setSearch] = useState("");
  const [archived, setArchived] = useState(false);
  const projects = useProjectCatalog(
    identity.workspace_id,
    useDeferredValue(search.trim()),
    archived,
  );
  const items = projects.data?.pages.flatMap((p) => p.items) ?? [];

  return (
    <section className="studio-page">
      <header className="studio-page__header studio-page__header--split">
        <div>
          <p className="studio-eyebrow">Workspace / {identity.workspace_id}</p>
          <h1>项目</h1>
          <p>打开作品继续创作，归档后可随时恢复。</p>
        </div>
        <Badge tone="info">已载入 {items.length} 个项目</Badge>
      </header>
      <div className="studio-action-row">
        <label>
          搜索项目
          <input value={search} maxLength={200} onChange={(e) => setSearch(e.target.value)} />
        </label>
        <label>
          <input
            type="checkbox"
            checked={archived}
            onChange={(e) => setArchived(e.target.checked)}
          />
          查看已归档
        </label>
      </div>
      {projects.isPending ? <StateResolver state="loading" /> : null}
      {projects.error ? (
        <StateResolver error={projects.error} onRetry={() => void projects.refetch()} />
      ) : null}
      {!projects.isPending && !projects.error && items.length === 0 ? (
        <EmptyState description="可修改搜索条件，或创建一个新项目。" title="没有符合条件的项目" />
      ) : items.length ? (
        <Table caption="当前 Workspace 的 Project">
          <TableHead>
            <tr>
              <th scope="col">名称</th>
              <th scope="col">状态</th>
              <th scope="col">更新时间</th>
              <th scope="col">操作</th>
            </tr>
          </TableHead>
          <TableBody>
            {items.map((project) => (
              <tr key={project.id}>
                <td>{project.name}</td>
                <td>{project.status === "active" ? "可用" : "已归档"}</td>
                <td>{new Date(project.updated_at).toLocaleString("zh-CN")}</td>
                <td>
                  <Link href={`/projects/${encodeURIComponent(project.id)}`}>打开</Link>
                  <ProjectActions project={project} />
                </td>
              </tr>
            ))}
          </TableBody>
        </Table>
      ) : null}
      {projects.hasNextPage ? (
        <Button busy={projects.isFetchingNextPage} onClick={() => void projects.fetchNextPage()}>
          更多项目
        </Button>
      ) : null}

      <ProjectCreatePanel
        canWrite={canWriteProjects(identity)}
        workspaceId={identity.workspace_id}
      />
    </section>
  );
}
