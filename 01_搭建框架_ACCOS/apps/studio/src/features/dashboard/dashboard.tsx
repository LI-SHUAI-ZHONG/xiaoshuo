"use client";

import { Badge, EmptyState } from "@accos/ui";
import Link from "next/link";

import { StateResolver } from "../../components/state-resolver";
import {
  useAgentsQuery,
  useAssetsQuery,
  useHealthQuery,
  useProjectsQuery,
  useWorkspaceQuery,
} from "../../lib/api/queries";
import { useIdentity } from "../../providers/identity-provider";
import { ProjectCreatePanel } from "../projects/project-create-panel";
import { canWriteProjects } from "../projects/permissions";

function ProjectAssetCount({ projectId, workspaceId }: { projectId: string; workspaceId: string }) {
  const query = useAssetsQuery(workspaceId, projectId);
  if (query.isPending) return <span className="studio-muted">读取中</span>;
  if (query.isError) return <span className="studio-danger-text">不可用</span>;
  return <span>{query.data.page.total}</span>;
}

function RuntimeSummary() {
  const health = useHealthQuery();
  const agents = useAgentsQuery();
  const degraded = health.data?.checks.filter((check) => check.status !== "healthy").length;

  return (
    <section className="studio-section-stack">
      <div className="studio-section-heading">
        <div>
          <p className="studio-eyebrow">Runtime</p>
          <h2>真实运行摘要</h2>
        </div>
        <Link href="/system">查看 System</Link>
      </div>
      <div className="studio-metric-grid">
        <article className="studio-metric-card">
          <span>API readiness</span>
          <strong>{health.isPending ? "读取中" : (health.data?.status ?? "不可用")}</strong>
        </article>
        <article className="studio-metric-card">
          <span>异常依赖</span>
          <strong>{health.isPending ? "读取中" : (degraded ?? "不可用")}</strong>
        </article>
        <article className="studio-metric-card">
          <span>注册 Agent Descriptor</span>
          <strong>{agents.isPending ? "读取中" : (agents.data?.items.length ?? "不可用")}</strong>
        </article>
      </div>
      {health.isError || agents.isError ? (
        <p className="studio-readonly-note">
          部分运行摘要暂不可用；页面没有以浏览器默认值替代服务端事实。
        </p>
      ) : null}
    </section>
  );
}

export function Dashboard() {
  const identity = useIdentity();
  const workspaceId = identity.workspace_id;
  const workspace = useWorkspaceQuery(workspaceId);
  const projects = useProjectsQuery(workspaceId);

  if (workspace.isPending || projects.isPending) return <StateResolver state="loading" />;
  if (workspace.isError)
    return <StateResolver error={workspace.error} onRetry={() => void workspace.refetch()} />;
  if (projects.isError)
    return <StateResolver error={projects.error} onRetry={() => void projects.refetch()} />;

  return (
    <section className="studio-page">
      <header className="studio-page__header studio-page__header--split">
        <div>
          <p className="studio-eyebrow">当前工作区</p>
          <h1>创作概览</h1>
          <p>项目和资产数量均来自当前 Workspace API。</p>
        </div>
        <Badge tone={workspace.data.archived ? "warning" : "success"}>
          {workspace.data.archived ? "已归档" : "可用"}
        </Badge>
      </header>

      <div className="studio-metric-grid">
        <article className="studio-metric-card">
          <span>Workspace</span>
          <strong className="studio-code-value">{workspace.data.id}</strong>
        </article>
        <article className="studio-metric-card">
          <span>可访问 Project</span>
          <strong>{projects.data.page.total}</strong>
        </article>
        <article className="studio-metric-card">
          <span>权限策略</span>
          <strong className="studio-code-value">{identity.policy_version}</strong>
        </article>
      </div>

      <RuntimeSummary />

      {projects.data.items.length === 0 ? (
        <>
          <EmptyState
            action={
              canWriteProjects(identity) ? (
                <a className="studio-link-button" href="#create-project">
                  创建空项目
                </a>
              ) : undefined
            }
            description={
              canWriteProjects(identity)
                ? "当前 Workspace 尚无 Project，可从一个空容器开始。"
                : "当前 Workspace 尚无可访问的 Project，且当前身份只有读取权限。"
            }
            title="暂无 Project"
          />
          <ProjectCreatePanel canWrite={canWriteProjects(identity)} workspaceId={workspaceId} />
        </>
      ) : (
        <section className="studio-section-stack">
          <div className="studio-section-heading">
            <div>
              <p className="studio-eyebrow">Project</p>
              <h2>继续工作</h2>
            </div>
            <Link href="/projects">查看全部</Link>
          </div>
          <div className="studio-project-grid">
            {projects.data.items.map((project) => (
              <Link
                className="studio-project-card"
                href={`/projects/${project.id}`}
                key={project.id}
              >
                <div>
                  <Badge tone={project.status === "active" ? "success" : "warning"}>
                    {project.status === "active" ? "可用" : "已归档"}
                  </Badge>
                  <h3>{project.name}</h3>
                </div>
                <dl>
                  <div>
                    <dt>Artifacts</dt>
                    <dd>进入项目查看</dd>
                  </div>
                  <div>
                    <dt>Assets</dt>
                    <dd>
                      <ProjectAssetCount projectId={project.id} workspaceId={workspaceId} />
                    </dd>
                  </div>
                </dl>
              </Link>
            ))}
          </div>
          <ProjectCreatePanel canWrite={canWriteProjects(identity)} workspaceId={workspaceId} />
        </section>
      )}
    </section>
  );
}
