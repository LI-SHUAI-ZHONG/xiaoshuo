"use client";

import { Button, Dialog } from "@accos/ui";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useIdentity } from "../providers/identity-provider";
import { useAuth } from "../providers/auth-provider";
import { useUiStore } from "../stores/ui-store";
import { ConnectedNetworkStatus } from "./network-status";
import { ScopeSwitcher } from "./scope-switcher";

const navigation = [
  { href: "/dashboard", label: "概览" },
  { href: "/projects", label: "Projects" },
  { href: "/feedback", label: "反馈" },
  { href: "/system", label: "System" },
  { href: "/settings", label: "Settings" },
  { href: "/workspaces", label: "工作区" },
  { href: "/status", label: "前端状态" },
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const identity = useIdentity();
  const { logout, error: authError } = useAuth();
  const commandOpen = useUiStore((state) => state.commandOpen);
  const setCommandOpen = useUiStore((state) => state.setCommandOpen);
  const sidebarOpen = useUiStore((state) => state.sidebarOpen);
  const setSidebarOpen = useUiStore((state) => state.setSidebarOpen);

  useEffect(() => {
    function handleShortcut(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandOpen(true);
      }
    }
    window.addEventListener("keydown", handleShortcut);
    return () => {
      window.removeEventListener("keydown", handleShortcut);
    };
  }, [setCommandOpen]);

  return (
    <div className="studio-shell">
      <header className="studio-topbar">
        <Button
          aria-controls="studio-navigation"
          aria-expanded={sidebarOpen}
          aria-label="切换导航"
          className="studio-menu-button"
          onClick={() => {
            setSidebarOpen(!sidebarOpen);
          }}
          variant="ghost"
        >
          ☰
        </Button>
        <Link className="studio-brand" href="/workspaces">
          <span aria-hidden="true" className="studio-brand__mark">
            A
          </span>
          <span>ACCOS Studio</span>
        </Link>
        <div className="studio-command-area">
          <Button
            onClick={() => {
              setCommandOpen(true);
            }}
            variant="secondary"
          >
            命令区 <kbd>Ctrl K</kbd>
          </Button>
        </div>
        <details className="studio-user-menu">
          <summary aria-label="打开用户与 Workspace 菜单">
            <span aria-hidden="true">○</span>
            <span>当前身份</span>
          </summary>
          <div className="studio-user-menu__panel">
            <strong>{identity.actor_kind === "user" ? "用户" : "服务身份"}</strong>
            <span>{identity.actor_id}</span>
            <span>Workspace：{identity.workspace_id}</span>
            <Button
              onClick={() => {
                void logout();
              }}
              variant="secondary"
            >
              退出当前会话
            </Button>
            {authError ? <p role="alert">{authError}</p> : null}
          </div>
        </details>
      </header>

      <aside
        className={`studio-sidebar ${sidebarOpen ? "studio-sidebar--open" : ""}`}
        id="studio-navigation"
      >
        <ScopeSwitcher />
        <nav aria-label="全局导航">
          <ul>
            {navigation.map((item) => (
              <li key={item.href}>
                <Link
                  aria-current={
                    pathname === item.href ||
                    (item.href === "/projects" && pathname.startsWith("/projects/"))
                      ? "page"
                      : undefined
                  }
                  href={item.href}
                  onClick={() => {
                    setSidebarOpen(false);
                  }}
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </aside>

      <main className="studio-main" id="main-content">
        <ConnectedNetworkStatus />
        {children}
      </main>

      <Dialog
        description="后续页面将在这里注册可搜索操作。当前没有可执行命令。"
        onOpenChange={setCommandOpen}
        open={commandOpen}
        title="命令区"
      >
        <p className="studio-muted">所有远期功能开关关闭时，命令区保持真实空状态。</p>
      </Dialog>
    </div>
  );
}
