"use client";

import { Badge } from "@accos/ui";
import Link from "next/link";

import { useIdentity } from "../../providers/identity-provider";
import { useProject } from "../../providers/scope-providers";
import { canWriteProject } from "./permissions";

export type ProjectSection =
  "agents" | "knowledge" | "memory" | "models" | "quality" | "studio" | "workflows" | "writing";

export function ProjectHeader({
  active,
  artifactId,
  eyebrow,
  title,
}: {
  active: ProjectSection;
  artifactId?: string;
  eyebrow: string;
  title?: string;
}) {
  const project = useProject();
  const identity = useIdentity();
  const canWrite = canWriteProject(identity, project);
  const links = [
    { href: `/projects/${project.id}`, id: "studio", label: "Project Studio" },
    { href: `/projects/${project.id}/knowledge`, id: "knowledge", label: "Knowledge" },
    { href: `/projects/${project.id}/memory`, id: "memory", label: "Memory" },
    { href: `/projects/${project.id}/workflows`, id: "workflows", label: "Workflows" },
    { href: `/projects/${project.id}/agents`, id: "agents", label: "Agents" },
    { href: `/projects/${project.id}/models`, id: "models", label: "模型调用" },
    { href: `/projects/${project.id}/quality`, id: "quality", label: "Quality" },
  ] as const;

  return (
    <>
      <header className="studio-page__header studio-page__header--split">
        <div>
          <p className="studio-eyebrow">{eyebrow}</p>
          <h1>{title ?? project.name}</h1>
          <p className="studio-code-line">Project / {project.id}</p>
        </div>
        <Badge tone={canWrite ? "success" : "warning"}>
          {project.status === "archived" ? "已归档" : canWrite ? "可编辑" : "只读"}
        </Badge>
      </header>
      <nav aria-label="Project 工作区" className="studio-project-nav">
        {links.map((link) => (
          <Link
            aria-current={active === link.id ? "page" : undefined}
            href={link.href}
            key={link.id}
          >
            {link.label}
          </Link>
        ))}
        {artifactId ? (
          <Link
            aria-current={active === "writing" ? "page" : undefined}
            href={`/projects/${project.id}/write/${artifactId}`}
          >
            Writing
          </Link>
        ) : null}
      </nav>
    </>
  );
}
