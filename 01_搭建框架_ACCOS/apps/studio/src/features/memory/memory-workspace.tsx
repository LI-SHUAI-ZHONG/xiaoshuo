"use client";

import type { components } from "@accos/api-client";
import { Badge, Button, EmptyState, Input, Select, Table, TableBody, TableHead } from "@accos/ui";
import { useState, type SyntheticEvent } from "react";

import { InlineApiError } from "../../components/inline-api-error";
import { StateResolver } from "../../components/state-resolver";
import { useCreateMemoryMutation } from "../../lib/api/mutations";
import { useMemoryQuery } from "../../lib/api/queries";
import { useIdentity } from "../../providers/identity-provider";
import { useProject } from "../../providers/scope-providers";
import { canWriteProject } from "../projects/permissions";
import { ProjectHeader } from "../projects/project-header";

type WritableMemoryScope = components["schemas"]["MemoryWriteRequest"]["scope"];

function currentLocalDateTime(): string {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

export function MemoryWorkspace() {
  const project = useProject();
  const identity = useIdentity();
  const canWrite = canWriteProject(identity, project);
  const createMemory = useCreateMemoryMutation(project.workspace_id, project.id);
  const [lookupId, setLookupId] = useState("");
  const [memoryId, setMemoryId] = useState("");
  const [scopeFilter, setScopeFilter] = useState<"all" | components["schemas"]["MemoryScope"]>(
    "all",
  );
  const [typeFilter, setTypeFilter] = useState("");
  const [scope, setScope] = useState<WritableMemoryScope>("project");
  const [memoryType, setMemoryType] = useState("technical_note");
  const [content, setContent] = useState("");
  const [provenanceKind, setProvenanceKind] = useState("studio_input");
  const [provenanceReference, setProvenanceReference] = useState("studio-form://memory");
  const [observedAt, setObservedAt] = useState(currentLocalDateTime);
  const memory = useMemoryQuery(project.workspace_id, project.id, memoryId);

  const matchesFilter =
    memory.data &&
    (scopeFilter === "all" || memory.data.scope === scopeFilter) &&
    (!typeFilter.trim() || memory.data.memory_type === typeFilter.trim());

  function lookup(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = lookupId.trim();
    if (normalized) setMemoryId(normalized);
  }

  function submitMemory(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedContent = content.trim();
    const normalizedType = memoryType.trim();
    const normalizedKind = provenanceKind.trim();
    const normalizedReference = provenanceReference.trim();
    if (!normalizedContent || !normalizedType || !normalizedKind || !normalizedReference) return;
    const timestamp = new Date(observedAt).toISOString();
    createMemory.mutate(
      {
        confidence: 0.5,
        content: normalizedContent,
        importance: 0.5,
        memory_type: normalizedType,
        observed_at: timestamp,
        provenance_kind: normalizedKind,
        provenance_reference: normalizedReference,
        retention_kind: "keep",
        scope,
        valid_from: timestamp,
      },
      {
        onSuccess(created) {
          setMemoryId(created.id);
          setLookupId(created.id);
          setContent("");
        },
      },
    );
  }

  return (
    <section className="studio-page">
      <ProjectHeader active="memory" eyebrow="Memory Workspace" />

      <section className="studio-panel">
        <div className="studio-section-heading">
          <div>
            <p className="studio-eyebrow">Filter / Lookup</p>
            <h2>读取技术 Memory</h2>
          </div>
        </div>
        <form className="studio-form-grid studio-form-grid--lookup" onSubmit={lookup}>
          <Input
            label="Memory ID"
            onChange={(event) => {
              setLookupId(event.target.value);
            }}
            placeholder="输入 UUID"
            value={lookupId}
          />
          <Select
            label="Scope 筛选"
            onChange={(event) => {
              setScopeFilter(event.target.value as typeof scopeFilter);
            }}
            value={scopeFilter}
          >
            <option value="all">全部 scope</option>
            <option value="working">working</option>
            <option value="session">session</option>
            <option value="project">project</option>
            <option value="universe">universe</option>
            <option value="creator">creator</option>
            <option value="experience">experience</option>
            <option value="wisdom">wisdom</option>
          </Select>
          <Input
            label="Type 筛选"
            onChange={(event) => {
              setTypeFilter(event.target.value);
            }}
            placeholder="例如 technical_note"
            value={typeFilter}
          />
          <Button disabled={!lookupId.trim()} type="submit">
            读取
          </Button>
        </form>
      </section>

      {memoryId && memory.isPending ? <StateResolver state="loading" /> : null}
      {memory.isError ? <InlineApiError error={memory.error} title="无法读取 Memory" /> : null}
      {memory.data && matchesFilter ? (
        <section className="studio-panel">
          <div className="studio-section-heading">
            <div>
              <p className="studio-eyebrow">Memory Record</p>
              <h2>{memory.data.memory_type}</h2>
            </div>
            <Badge tone={memory.data.current ? "success" : "warning"}>{memory.data.status}</Badge>
          </div>
          <Table caption="Memory 技术记录">
            <TableHead>
              <tr>
                <th scope="col">Scope</th>
                <th scope="col">Type</th>
                <th scope="col">内容</th>
                <th scope="col">来源</th>
                <th scope="col">版本</th>
              </tr>
            </TableHead>
            <TableBody>
              <tr>
                <td>{memory.data.scope}</td>
                <td>{memory.data.memory_type}</td>
                <td>{memory.data.content}</td>
                <td className="studio-code-value">
                  {memory.data.provenance.kind} / {memory.data.provenance.reference}
                </td>
                <td>{memory.data.version}</td>
              </tr>
            </TableBody>
          </Table>
        </section>
      ) : null}
      {memory.data && !matchesFilter ? (
        <EmptyState
          description="记录存在，但不符合当前 scope/type 筛选条件。"
          title="筛选结果为空"
        />
      ) : null}
      {!memoryId ? (
        <EmptyState
          description="当前 API 未公开 Memory 集合列表；输入真实 ID 或创建一条技术记录后查看。"
          title="尚未选择 Memory"
        />
      ) : null}

      {canWrite ? (
        <section className="studio-panel">
          <div className="studio-section-heading">
            <div>
              <p className="studio-eyebrow">Technical Record</p>
              <h2>创建 Memory</h2>
            </div>
          </div>
          <form className="studio-form-grid" onSubmit={submitMemory}>
            <Select
              label="Scope"
              onChange={(event) => {
                setScope(event.target.value as WritableMemoryScope);
              }}
              value={scope}
            >
              <option value="working">working</option>
              <option value="session">session</option>
              <option value="project">project</option>
            </Select>
            <Input
              label="Memory type"
              maxLength={100}
              onChange={(event) => {
                setMemoryType(event.target.value);
              }}
              pattern="[a-z][a-z0-9_.-]*"
              required
              value={memoryType}
            />
            <Input
              label="技术内容"
              maxLength={20_000}
              onChange={(event) => {
                setContent(event.target.value);
              }}
              placeholder="输入无业务含义的技术记录"
              required
              value={content}
            />
            <Input
              label="观测时间"
              onChange={(event) => {
                setObservedAt(event.target.value);
              }}
              required
              type="datetime-local"
              value={observedAt}
            />
            <Input
              label="来源类型"
              maxLength={100}
              onChange={(event) => {
                setProvenanceKind(event.target.value);
              }}
              pattern="[a-z][a-z0-9_.-]*"
              required
              value={provenanceKind}
            />
            <Input
              label="来源引用"
              maxLength={500}
              onChange={(event) => {
                setProvenanceReference(event.target.value);
              }}
              required
              value={provenanceReference}
            />
            <Button busy={createMemory.isPending} type="submit">
              创建技术记录
            </Button>
          </form>
          {createMemory.data ? (
            <p className="studio-success-text" role="status">
              Memory {createMemory.data.id} 已保存并载入。
            </p>
          ) : null}
          {createMemory.isError ? (
            <InlineApiError error={createMemory.error} title="Memory 创建失败" />
          ) : null}
        </section>
      ) : (
        <p className="studio-readonly-note">当前身份仅可读取，Memory 写入表单已隐藏。</p>
      )}
    </section>
  );
}
