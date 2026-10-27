import { Badge } from "@accos/ui";
import Link from "next/link";

export default function PublicStatusPage() {
  return (
    <main className="studio-public" id="main-content">
      <section className="studio-public__card">
        <Badge tone="success">前端可用</Badge>
        <h1>ACCOS Studio 状态</h1>
        <p>Studio 壳已加载。受保护的 API 与依赖健康状态仅在有效身份和 Workspace 作用域内查询。</p>
        <Link className="studio-link-button" href="/workspaces">
          进入工作台
        </Link>
      </section>
    </main>
  );
}
