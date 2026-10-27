"use client";

import { Table, TableBody, TableHead } from "@accos/ui";
import Link from "next/link";

import { StateResolver } from "../../../../components/state-resolver";
import { useProjectsQuery } from "../../../../lib/api/queries";
import { useWorkspace } from "../../../../providers/scope-providers";

export default function WorkspacePage() {
  const workspace = useWorkspace();
  const query = useProjectsQuery(workspace.id);
  if (query.isPending) return <StateResolver state="loading" />;
  if (query.isError)
    return <StateResolver error={query.error} onRetry={() => void query.refetch()} />;
  if (query.data.items.length === 0) return <StateResolver state="empty-projects" />;

  return (
    <section className="studio-page">
      <header className="studio-page__header">
        <h1>Project</h1>
        <p>当前 Workspace：{workspace.id}</p>
      </header>
      <Table caption="可访问的 Project">
        <TableHead>
          <tr>
            <th scope="col">名称</th>
            <th scope="col">状态</th>
            <th scope="col">操作</th>
          </tr>
        </TableHead>
        <TableBody>
          {query.data.items.map((project) => (
            <tr key={project.id}>
              <td>{project.name}</td>
              <td>{project.status === "active" ? "可用" : "已归档"}</td>
              <td>
                <Link href={`/projects/${encodeURIComponent(project.id)}`}>打开</Link>
              </td>
            </tr>
          ))}
        </TableBody>
      </Table>
    </section>
  );
}
