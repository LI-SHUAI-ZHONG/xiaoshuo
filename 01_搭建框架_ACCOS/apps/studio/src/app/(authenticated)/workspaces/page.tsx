"use client";

import { Table, TableBody, TableHead } from "@accos/ui";
import Link from "next/link";

import { StateResolver } from "../../../components/state-resolver";
import { useWorkspacesQuery } from "../../../lib/api/queries";

export default function WorkspacesPage() {
  const query = useWorkspacesQuery();
  if (query.isPending) return <StateResolver state="loading" />;
  if (query.isError)
    return <StateResolver error={query.error} onRetry={() => void query.refetch()} />;
  if (query.data.items.length === 0) return <StateResolver state="empty-workspaces" />;

  return (
    <section className="studio-page">
      <header className="studio-page__header">
        <h1>Workspace</h1>
        <p>列表来自当前身份可见的 API 资源。</p>
      </header>
      <Table caption="可访问的 Workspace">
        <TableHead>
          <tr>
            <th scope="col">Workspace ID</th>
            <th scope="col">状态</th>
            <th scope="col">操作</th>
          </tr>
        </TableHead>
        <TableBody>
          {query.data.items.map((workspace) => (
            <tr key={workspace.id}>
              <td>{workspace.id}</td>
              <td>{workspace.archived ? "已归档" : "可用"}</td>
              <td>
                <Link href={`/workspaces/${encodeURIComponent(workspace.id)}`}>打开</Link>
              </td>
            </tr>
          ))}
        </TableBody>
      </Table>
    </section>
  );
}
