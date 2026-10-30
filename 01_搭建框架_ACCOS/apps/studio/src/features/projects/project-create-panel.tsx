"use client";

import { Button, Input } from "@accos/ui";
import { useRouter } from "next/navigation";
import { useState, type SyntheticEvent } from "react";

import { InlineApiError } from "../../components/inline-api-error";
import { useCreateProjectMutation } from "../../lib/api/mutations";

export function ProjectCreatePanel({
  canWrite,
  workspaceId,
}: {
  canWrite: boolean;
  workspaceId: string;
}) {
  const [name, setName] = useState("");
  const mutation = useCreateProjectMutation(workspaceId);
  const router = useRouter();

  if (!canWrite) return null;

  function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    mutation.mutate(
      { name: trimmed },
      {
        onSuccess(project) {
          setName("");
          router.push(`/projects/${encodeURIComponent(project.id)}`);
        },
      },
    );
  }

  return (
    <section className="studio-panel" id="create-project">
      <div className="studio-panel__heading">
        <div>
          <p className="studio-eyebrow">空项目</p>
          <h2>创建 Project</h2>
        </div>
        <span className="studio-panel__index" aria-hidden="true">
          +
        </span>
      </div>
      <form className="studio-form-row" onSubmit={submit}>
        <Input
          autoComplete="off"
          label="Project 名称"
          maxLength={200}
          onChange={(event) => {
            setName(event.target.value);
          }}
          placeholder="输入空项目名称"
          required
          value={name}
        />
        <Button busy={mutation.isPending} type="submit">
          创建空项目
        </Button>
      </form>
      {mutation.isError ? <InlineApiError error={mutation.error} title="创建失败" /> : null}
    </section>
  );
}
