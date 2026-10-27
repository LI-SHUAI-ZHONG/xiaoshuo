"use client";

import { Button, EmptyState, ErrorState, Skeleton } from "@accos/ui";
import Link from "next/link";
import type { ReactNode } from "react";

import { asApiProblem } from "../lib/api/errors";
import { LocalSessionForm } from "./local-session-form";

export type ViewState =
  | "degraded"
  | "empty-projects"
  | "empty-workspaces"
  | "forbidden"
  | "loading"
  | "not-found"
  | "offline"
  | "unauthenticated";

export interface StateResolverProps {
  error?: unknown;
  onRetry?: (() => void) | undefined;
  state?: ViewState;
}

function StateLink({ href, children }: { children: ReactNode; href: string }) {
  return (
    <Link className="studio-link-button" href={href}>
      {children}
    </Link>
  );
}

export function StateResolver({ error, onRetry, state }: StateResolverProps) {
  if (state === "loading") {
    return (
      <section aria-label="内容正在加载" className="studio-state-wrap">
        <Skeleton lines={4} />
      </section>
    );
  }
  if (state === "unauthenticated") {
    return (
      <div className="studio-state-wrap">
        <EmptyState
          action={<StateLink href="/status">查看服务状态</StateLink>}
          description="Studio 没有收到有效会话。请通过已配置的身份提供方进入工作台。"
          title="需要登录"
        />
        <LocalSessionForm />
      </div>
    );
  }
  if (state === "forbidden") {
    return (
      <div className="studio-state-wrap">
        <ErrorState
          action={<StateLink href="/workspaces">返回工作区</StateLink>}
          description="当前身份没有访问此 Workspace 或 Project 的权限。"
          title="无权访问"
        />
      </div>
    );
  }
  if (state === "offline") {
    return (
      <div className="studio-state-wrap">
        <ErrorState
          description="网络不可用。恢复连接后可重试，现有 UI 草稿不会发送。"
          onRetry={onRetry}
          title="当前离线"
        />
      </div>
    );
  }
  if (state === "degraded") {
    return (
      <div className="studio-state-wrap">
        <ErrorState
          description="API 已响应，但一个或多个依赖暂不可用。请稍后重试。"
          onRetry={onRetry}
          title="服务降级"
        />
      </div>
    );
  }
  if (state === "not-found") {
    return (
      <div className="studio-state-wrap">
        <EmptyState
          action={<StateLink href="/workspaces">返回工作区</StateLink>}
          description="资源不存在，或已不在当前作用域中。"
          title="未找到内容"
        />
      </div>
    );
  }
  if (state === "empty-workspaces") {
    return (
      <EmptyState
        description="当前身份没有可用 Workspace。请联系管理员分配成员关系。"
        title="暂无 Workspace"
      />
    );
  }
  if (state === "empty-projects") {
    return <EmptyState description="此 Workspace 还没有可访问的 Project。" title="暂无 Project" />;
  }

  const problem = asApiProblem(error);
  if (problem.kind === "unauthenticated") return <StateResolver state="unauthenticated" />;
  if (problem.kind === "forbidden") return <StateResolver state="forbidden" />;
  if (problem.kind === "not-found") return <StateResolver state="not-found" />;
  if (problem.kind === "offline") return <StateResolver onRetry={onRetry} state="offline" />;
  if (problem.kind === "degraded") return <StateResolver onRetry={onRetry} state="degraded" />;
  return (
    <div className="studio-state-wrap">
      <ErrorState
        correlationId={problem.correlationId ?? undefined}
        description={problem.message}
        onRetry={onRetry}
        title="无法加载内容"
      />
    </div>
  );
}

export function RetryButton({ onRetry }: { onRetry: () => void }) {
  return <Button onClick={onRetry}>重试</Button>;
}
