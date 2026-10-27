"use client";

import type { components } from "@accos/api-client";
import { useQueryClient } from "@tanstack/react-query";
import { localDrafts } from "../features/writing/drafts";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

type SessionInfo = components["schemas"]["SessionInfo"];

export interface AuthSession {
  // Browser login uses HttpOnly cookies; nonempty tokens are explicit development fixtures only.
  accessToken: string;
  workspaceId: string;
  csrfToken?: string;
  userId?: string;
  sessionId?: string;
}
interface AuthContextValue {
  session: AuthSession | null;
  info: SessionInfo | null;
  loading: boolean;
  error: string | null;
  setSession: (session: AuthSession | null) => void;
  refresh: () => Promise<void>;
  accept: (info: SessionInfo) => void;
  logout: () => Promise<void>;
}
const AuthContext = createContext<AuthContextValue | null>(null);
export function AuthProvider({
  children,
  initialSession = null,
}: {
  children: ReactNode;
  initialSession?: AuthSession | null;
}) {
  const [session, updateSession] = useState<AuthSession | null>(initialSession);
  const [info, setInfo] = useState<SessionInfo | null>(null);
  const [loading, setLoading] = useState(initialSession === null);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const setSession = useCallback(
    (next: AuthSession | null) => {
      queryClient.clear();
      updateSession(next);
    },
    [queryClient],
  );
  const accept = useCallback(
    (data: SessionInfo) => {
      setInfo(data);
      setError(null);
      queryClient.clear();
      updateSession((previous) => {
        if (!data.authenticated || !data.user_id || !data.session_id || !data.csrf_token)
          return null;
        const workspace =
          previous?.userId === data.user_id &&
          data.workspaces?.some((w) => w.id === previous.workspaceId)
            ? previous.workspaceId
            : data.workspaces?.[0]?.id;
        if (!workspace) return null;
        return {
          accessToken: "",
          workspaceId: workspace,
          csrfToken: data.csrf_token,
          userId: data.user_id,
          sessionId: data.session_id,
        };
      });
    },
    [queryClient],
  );
  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch("/api/v1/auth/session", {
        credentials: "same-origin",
        cache: "no-store",
      });
      if (!response.ok) throw new Error("无法读取登录状态，请检查本地服务。");
      accept((await response.json()) as SessionInfo);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法连接本地服务");
    } finally {
      setLoading(false);
    }
  }, [accept]);
  const logout = useCallback(async () => {
    const promises: Promise<unknown>[] = [];
    if (
      !window.dispatchEvent(
        new CustomEvent("accos-before-logout", { cancelable: true, detail: { promises } }),
      )
    ) {
      setError("请先完成当前输入法组合，再退出。");
      return;
    }
    try {
      await Promise.all(promises);
      if (
        session?.userId &&
        (await localDrafts(session.userId)).length &&
        !window.confirm("仍有未同步正文。草稿将保留在此浏览器，仅同一账号可恢复；确认退出？")
      )
        return;
    } catch {
      setError("本机草稿尚未可靠写入。请先下载稿件或恢复本机存储，再退出。");
      return;
    }
    if (!session?.accessToken) {
      try {
        const response = await fetch("/api/v1/auth/logout", {
          method: "POST",
          credentials: "same-origin",
          headers: { "X-CSRF-Token": session?.csrfToken ?? "" },
        });
        if (!response.ok && response.status !== 401) throw new Error("退出失败，请重试。");
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : "退出失败");
        return;
      }
    }
    setSession(null);
    setInfo(null);
    await refresh();
  }, [session, setSession, refresh]);
  useEffect(() => {
    if (initialSession === null) void refresh();
  }, [initialSession, refresh]);
  useEffect(() => {
    const expires = info?.expires_at;
    if (!expires || !session) return;
    const timer = window.setTimeout(
      () => {
        void refresh();
      },
      Math.max(0, new Date(expires).getTime() - Date.now()),
    );
    return () => window.clearTimeout(timer);
  }, [info?.expires_at, session, refresh]);
  const value = useMemo(
    () => ({ session, info, loading, error, setSession, refresh, accept, logout }),
    [session, info, loading, error, setSession, refresh, accept, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider");
  return value;
}
