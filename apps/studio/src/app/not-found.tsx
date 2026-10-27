import { EmptyState } from "@accos/ui";
import Link from "next/link";

export default function NotFound() {
  return (
    <main className="studio-state-wrap" id="main-content">
      <EmptyState
        action={
          <Link className="studio-link-button" href="/workspaces">
            返回工作区
          </Link>
        }
        description="请求的 Studio 路由不存在。"
        title="页面未找到"
      />
    </main>
  );
}
