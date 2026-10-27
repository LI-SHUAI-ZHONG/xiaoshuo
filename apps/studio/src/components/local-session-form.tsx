"use client";

import type { components } from "@accos/api-client";
import { Button, Input } from "@accos/ui";
import Link from "next/link";
import { useState, type SyntheticEvent } from "react";
import { useAuth } from "../providers/auth-provider";

const oidcErrors = {
  cancelled: "已取消团队登录。你可以重新登录，或使用本地账号。",
  provider_failed: "团队身份服务未完成登录，请重试或使用本地账号。",
  failed: "团队登录已过期或验证失败，请重新发起登录。",
  membership_required: "该团队身份尚未获得工作区权限，请联系管理员分配成员资格。",
  configuration_required: "团队登录配置尚未就绪，请使用本地账号检查设置。",
};

export function LocalSessionForm({ oidcError = null }: { oidcError?: string | null }) {
  const { accept, info, error: connectionError, refresh, session } = useAuth();
  const setup = info?.bootstrap_required ?? false;
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [bootstrapToken, setBootstrapToken] = useState("");
  const [name, setName] = useState("我的创作空间");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const oidcMessage =
    oidcError !== null && Object.hasOwn(oidcErrors, oidcError)
      ? oidcErrors[oidcError as keyof typeof oidcErrors]
      : null;
  async function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(setup ? "/api/v1/auth/bootstrap" : "/api/v1/auth/login", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username,
          password,
          ...(setup ? { bootstrap_token: bootstrapToken, workspace_name: name } : {}),
        }),
      });
      if (!response.ok) {
        const messages: Record<number, string> = {
          401: "账号、密码或初始化凭据不正确。",
          409: "初始化已完成，请刷新后登录。",
          422: "请检查输入格式，初始密码至少 12 个字符。",
          429: "尝试过于频繁，请稍后再试。",
          503: "服务或初始化配置尚未准备好。",
        };
        throw new Error(messages[response.status] ?? "登录失败，请检查服务配置后重试。");
      }
      accept((await response.json()) as components["schemas"]["SessionInfo"]);
      setPassword("");
      setBootstrapToken("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法连接服务");
    } finally {
      setBusy(false);
    }
  }
  if (session)
    return (
      <section className="studio-panel">
        <h1>已登录</h1>
        <Link href="/dashboard">进入创作工作台</Link>
      </section>
    );
  return (
    <form className="studio-local-session studio-panel" onSubmit={(event) => void submit(event)}>
      <h1>{setup ? "初始化创作空间" : "登录创作空间"}</h1>
      <p>
        {setup
          ? "使用本地安装入口生成的一次性凭据建立作者账号。"
          : "使用本地账号登录，或选择已配置的团队身份。"}
      </p>
      {error || connectionError ? <p role="alert">{error || connectionError}</p> : null}
      {oidcMessage ? <p role="status">{oidcMessage}</p> : null}
      {connectionError ? (
        <Button onClick={() => void refresh()} type="button">
          重试连接
        </Button>
      ) : null}
      {setup ? (
        <>
          <Input
            label="一次性初始化凭据"
            type="password"
            autoComplete="off"
            value={bootstrapToken}
            onChange={(e) => setBootstrapToken(e.target.value)}
            required
          />
          <Input
            label="工作区名称"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={100}
            required
          />
        </>
      ) : null}
      <Input
        label="账号（至少 3 个英文字母或数字）"
        autoComplete="username"
        maxLength={100}
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        required
      />
      <Input
        label="密码"
        autoComplete={setup ? "new-password" : "current-password"}
        type="password"
        minLength={setup ? 12 : 1}
        maxLength={256}
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      <Button type="submit" busy={busy} disabled={!info}>
        {setup ? "建立作者账号" : "登录"}
      </Button>
      {info?.oidc_configured ? (
        <a className="studio-link-button" href="/api/v1/auth/oidc/start">
          使用团队身份登录
        </a>
      ) : null}
      {info?.authenticated && !info.workspaces?.length ? (
        <p role="status">已验证身份，但没有可用工作区。请让管理员分配成员权限。</p>
      ) : null}
    </form>
  );
}
