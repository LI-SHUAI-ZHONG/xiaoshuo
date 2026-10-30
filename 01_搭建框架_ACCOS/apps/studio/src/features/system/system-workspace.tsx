"use client";

import { Badge, Button, EmptyState, Table, TableBody, TableHead } from "@accos/ui";
import Link from "next/link";

import { StateResolver } from "../../components/state-resolver";
import { useHealthQuery, useModelStatusQuery, useSystemSettingsQuery } from "../../lib/api/queries";
import { StatusBadge } from "../monitoring/status-badge";
import { operationalState } from "../monitoring/status";

export function SystemWorkspace() {
  const health = useHealthQuery();
  const settings = useSystemSettingsQuery();
  const models = useModelStatusQuery();

  if (health.isPending || settings.isPending || models.isPending) {
    return <StateResolver state="loading" />;
  }
  if (health.isError)
    return <StateResolver error={health.error} onRetry={() => void health.refetch()} />;
  if (settings.isError)
    return <StateResolver error={settings.error} onRetry={() => void settings.refetch()} />;
  if (models.isError)
    return <StateResolver error={models.error} onRetry={() => void models.refetch()} />;

  const state = operationalState(health.data.status, health.data.checks);

  return (
    <section className="studio-page studio-page--wide">
      <header className="studio-page__header studio-page__header--split">
        <div>
          <p className="studio-eyebrow">System</p>
          <h1>运行状态与依赖诊断</h1>
          <p>状态来自当前 Workspace 的健康、配置与网关 API；每 30 秒重新读取。</p>
        </div>
        <StatusBadge status={state} />
      </header>

      <div className="studio-summary-strip">
        <div>
          <span>Live</span>
          <strong>alive</strong>
        </div>
        <div>
          <span>Ready</span>
          <strong>{health.data.status}</strong>
        </div>
        <div>
          <span>Operational</span>
          <strong>{state}</strong>
        </div>
      </div>

      <p className="studio-readonly-note">
        “alive”仅表示受保护的 System API 已响应；Worker 的配置、Outbox relay
        的配置不等于已证明存活或积压为零。
      </p>

      <section className="studio-panel">
        <div className="studio-panel__heading">
          <div>
            <p className="studio-eyebrow">Readiness</p>
            <h2>依赖检查</h2>
          </div>
          <div className="studio-action-row">
            <Badge tone="neutral">v{health.data.version}</Badge>
            <Button onClick={() => void health.refetch()} variant="secondary">
              立即刷新
            </Button>
          </div>
        </div>
        {health.data.checks.length === 0 ? (
          <EmptyState description="健康服务未返回依赖探针。" title="暂无依赖检查" />
        ) : (
          <Table caption="数据库、Redis、对象存储和 AI Provider 健康状态">
            <TableHead>
              <tr>
                <th scope="col">依赖</th>
                <th scope="col">关键</th>
                <th scope="col">诊断</th>
                <th scope="col">状态</th>
              </tr>
            </TableHead>
            <TableBody>
              {health.data.checks.map((check) => (
                <tr key={check.name}>
                  <td>{check.name}</td>
                  <td>{check.critical ? "是" : "否"}</td>
                  <td className="studio-code-value">{check.detail}</td>
                  <td>
                    <StatusBadge status={check.status} />
                  </td>
                </tr>
              ))}
            </TableBody>
          </Table>
        )}
        <p className="studio-muted">采样时间：{health.data.timestamp}</p>
      </section>

      <section className="studio-two-column">
        <article className="studio-panel">
          <div className="studio-panel__heading">
            <div>
              <p className="studio-eyebrow">Runtime boundaries</p>
              <h2>Worker / Outbox</h2>
            </div>
            <Badge tone="warning">非存活探针</Badge>
          </div>
          {settings.data.runtime_boundaries.map((boundary) => (
            <article className="studio-status-card" key={boundary.name}>
              <div className="studio-panel__heading">
                <strong>{boundary.name}</strong>
                <StatusBadge status={boundary.status} />
              </div>
              <p className="studio-code-line">{boundary.detail}</p>
            </article>
          ))}
        </article>

        <article className="studio-panel">
          <div className="studio-panel__heading">
            <div>
              <p className="studio-eyebrow">Model gateway</p>
              <h2>Fake / 外部 Provider</h2>
            </div>
            <Badge tone="neutral">{models.data.protocol_version}</Badge>
          </div>
          <dl className="studio-definition-list studio-definition-list--compact">
            <div>
              <dt>配置的 Provider</dt>
              <dd>{settings.data.ai_provider ?? "NOT_CONFIGURED"}</dd>
            </div>
            <div>
              <dt>真实 Provider 调用</dt>
              <dd>
                {settings.data.feature_flags.find((flag) => flag.name === "real_provider_calls")
                  ?.enabled
                  ? "enabled"
                  : "disabled"}
              </dd>
            </div>
          </dl>
          {models.data.providers.length === 0 ? (
            <EmptyState description="模型网关没有 Provider 状态。" title="NOT_CONFIGURED" />
          ) : (
            models.data.providers.map((provider) => (
              <article className="studio-status-card" key={provider.provider_id}>
                <div className="studio-panel__heading">
                  <strong>{provider.provider_id}</strong>
                  <StatusBadge status={provider.state} />
                </div>
                <p>
                  failures={provider.consecutive_failures}, in_flight={provider.in_flight}
                </p>
              </article>
            ))
          )}
        </article>
      </section>

      <div className="studio-action-row">
        <Link className="studio-link-button" href="/settings">
          查看脱敏设置与 Feature Flags
        </Link>
      </div>
    </section>
  );
}
