"use client";

import type { components } from "@accos/api-client";
import { useCallback, useEffect, useRef, useState } from "react";
import { asApiProblem } from "../../lib/api/errors";
import { useContentApi } from "./content-api";
import {
  draftKey,
  localDrafts,
  removeDraft,
  sameScope,
  saveDraft,
  type DraftScope,
  type LocalDraft,
} from "./drafts";
import { emptyDocument, type Document } from "./editor";

type Copy = components["schemas"]["WorkingCopy"];
type Merge = components["schemas"]["MergeResult"];
export type Choices = Record<string, "ours" | "theirs">;

export function useWritingCopy(
  actor: string,
  workspace: string,
  project: string,
  artifact: string,
  branch?: string,
) {
  const api = useContentApi(workspace, project, artifact);
  const [copy, setCopy] = useState<Copy | null>(null);
  const base = useRef<Copy | null>(null);
  const [document, setDocument] = useState<Document | null>(null);
  const [message, setMessage] = useState("正在加载正文…");
  const [error, setError] = useState<unknown>(null);
  const [recoveries, setRecoveries] = useState<LocalDraft[]>([]);
  const [conflict, setConflict] = useState<{ remote: Copy; result: Merge } | null>(null);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [isComposing, setIsComposing] = useState(false);
  const [resolving, setResolving] = useState(false);
  const draft = useRef<LocalDraft | null>(null);
  const recovered = useRef<LocalDraft | null>(null);
  const replica = useRef("");
  const saving = useRef(false);
  const composing = useRef(false);
  const alive = useRef(true);
  const blocked = useRef(false);
  const persistQueue = useRef(Promise.resolve());
  const persist = useCallback((value: LocalDraft) => {
    // Serialize rapid keystrokes; older async writes must not overwrite newer local drafts.
    const next = persistQueue.current.catch(() => undefined).then(() => saveDraft(value));
    persistQueue.current = next;
    return next;
  }, []);
  const load = useCallback(async () => {
    if (draft.current || composing.current) return;
    let drafts: LocalDraft[] = [];
    try {
      drafts = (await localDrafts(actor)).filter(
        (d) =>
          d.scope.workspace === workspace &&
          d.scope.project === project &&
          d.scope.artifact === artifact &&
          (!branch || d.scope.branch === branch),
      );
      if (alive.current) setRecoveries(drafts);
    } catch (cause) {
      if (alive.current) setError(cause);
    }
    let value: Copy;
    try {
      value = await api.working(branch);
    } catch (cause) {
      if (alive.current)
        setMessage(
          drafts.length
            ? "服务器暂不可达，可以恢复或下载本机稿，联网后核对版本。"
            : "无法读取服务器正文，请重试。",
        );
      throw cause;
    }
    if (!alive.current || draft.current || composing.current) return;
    base.current = value;
    setCopy(value);
    setDocument(value.document?.content.length ? value.document : emptyDocument());
    setMessage(
      value.content_status.startsWith("legacy")
        ? "旧记录没有可确认的正文，可另存新稿。"
        : "已读取服务器正文",
    );
    const scope = { actor, workspace, project, artifact, branch: value.branch.id };
    setRecoveries(drafts.filter((d) => sameScope(d.scope, scope)));
  }, [api, actor, workspace, project, artifact, branch]);
  useEffect(() => {
    alive.current = true;
    replica.current = crypto.randomUUID();
    void load().catch(setError);
    return () => {
      alive.current = false;
    };
  }, [load]);
  const change = useCallback(
    (value: Document) => {
      const current = base.current;
      if (!current) return;
      const scope: DraftScope = { actor, workspace, project, artifact, branch: current.branch.id };
      const next: LocalDraft = {
        ...(draft.current ?? {}),
        scope,
        key: draftKey(scope, replica.current),
        document: value,
        baseRevision: draft.current
          ? draft.current.baseRevision
          : (current.branch.head_revision_id ?? null),
        version: draft.current?.version ?? current.branch.version,
        epoch: draft.current?.epoch ?? current.branch.document_epoch,
        changeId: crypto.randomUUID(),
        updatedAt: Date.now(),
      };
      draft.current = next;
      setDocument(value);
      setDirty(true);
      setError(null);
      setMessage("正在保留本机草稿…");
      void persist(next)
        .then(() => {
          if (alive.current && draft.current?.changeId === next.changeId)
            setMessage("本机草稿已保留，等待同步");
        })
        .catch((cause: unknown) => {
          setError(cause);
          setMessage("本机存储失败，请立即下载草稿；页面内容仍在");
        });
    },
    [actor, workspace, project, artifact, persist],
  );
  const save = useCallback(async () => {
    const value = draft.current;
    if (!value || saving.current || composing.current || blocked.current) return;
    if (!navigator.onLine) {
      setMessage("离线：仅保存在本机，联网后重试");
      return;
    }
    saving.current = true;
    setBusy(true);
    try {
      const pending = value.pending ?? {
        body: {
          document: value.document,
          client_change_id: value.changeId,
          base_revision_id: value.baseRevision,
          document_epoch: value.epoch,
        },
        version: value.version,
      };
      const journal = { ...value, pending };
      draft.current = journal;
      await persist(journal);
      setMessage("正在保存到服务器…");
      const revision = await api.save(value.scope.branch, pending.version, pending.body);
      if (!alive.current) {
        // Do not lose newer keystrokes if navigation happened during this request.
        await persistQueue.current;
        if (draft.current?.changeId === pending.body.client_change_id) await removeDraft(journal);
        return;
      }
      const current = base.current;
      if (!current) return;
      const nextBase: Copy = {
        ...current,
        revision,
        content_status: "available",
        document: pending.body.document,
        text: null,
        branch: {
          ...current.branch,
          head_revision_id: revision.id,
          version: revision.working_version,
          document_epoch: revision.document_epoch,
        },
      };
      base.current = nextBase;
      setCopy(nextBase);
      await persistQueue.current;
      let latest: LocalDraft | null = draft.current;
      if (latest?.changeId === pending.body.client_change_id) {
        const recoveredKey = recovered.current?.key;
        await removeDraft(latest);
        if (recovered.current) await removeDraft(recovered.current);
        recovered.current = null;
        // A keystroke can arrive during the IndexedDB transaction above.
        if (draft.current?.changeId === pending.body.client_change_id) {
          draft.current = null;
          setDirty(false);
          setMessage("已保存到服务器");
          setRecoveries((old) =>
            old.filter(
              (item) =>
                item.key !== recoveredKey && item.changeId !== pending.body.client_change_id,
            ),
          );
        }
      }
      latest = draft.current;
      if (latest) {
        const { pending: _oldPending, ...rest } = latest;
        const rebased: LocalDraft = {
          ...rest,
          baseRevision: revision.id,
          version: revision.working_version,
          epoch: revision.document_epoch,
        };
        draft.current = rebased;
        await persist(rebased);
        setMessage("上一版已保存，后续输入保留在本机");
      }
      setError(null);
    } catch (cause) {
      if (!alive.current) return;
      const problem = asApiProblem(cause);
      if (problem.kind === "conflict") {
        blocked.current = true;
        setResolving(true);
        setMessage("版本冲突：本机与服务器稿件均已保留");
        try {
          const remote = await api.working(value.scope.branch);
          const local = draft.current ?? value;
          if (
            remote.branch.document_epoch !== local.epoch ||
            remote.branch.editing_mode !== "solo"
          ) {
            setError(
              new Error("编辑通道已切换。请下载本机稿并重新打开文档，不能覆盖新的协作版本。"),
            );
          } else {
            const result = await api.reconcile({
              base_revision_id: local.baseRevision,
              current_revision_id: remote.branch.head_revision_id ?? null,
              document: local.document,
              resolutions: {},
            });
            if (draft.current?.changeId === local.changeId) setConflict({ remote, result });
            else setError(new Error("合并预览期间输入发生变化，请点击保存重新核对。"));
          }
        } catch (mergeError) {
          setError(mergeError);
        }
      } else {
        setError(cause);
        if (problem.kind === "forbidden" || problem.kind === "unauthenticated")
          blocked.current = true;
        setMessage(
          problem.kind === "offline"
            ? "离线：仅保存在本机，联网后重试"
            : "服务器未确认保存，本机草稿已保留",
        );
      }
    } finally {
      saving.current = false;
      if (alive.current) {
        setBusy(false);
        setResolving(false);
      }
    }
  }, [api, persist]);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (dirty && !conflict && !error) void save();
    }, 1200);
    return () => clearTimeout(timer);
  }, [document, dirty, busy, conflict, error, isComposing, save]);
  useEffect(() => {
    const online = () => {
      void save();
    };
    const leaving = (event: BeforeUnloadEvent) => {
      if (draft.current || composing.current) {
        event.preventDefault();
        event.returnValue = "";
      }
    };
    const logout = (event: Event) => {
      if (composing.current) event.preventDefault();
      const promises = (event as CustomEvent<{ promises: Promise<unknown>[] }>).detail.promises;
      promises.push(persistQueue.current);
    };
    window.addEventListener("online", online);
    window.addEventListener("beforeunload", leaving);
    window.addEventListener("accos-before-logout", logout);
    return () => {
      window.removeEventListener("online", online);
      window.removeEventListener("beforeunload", leaving);
      window.removeEventListener("accos-before-logout", logout);
    };
  }, [save]);
  async function recover(value: LocalDraft) {
    if (saving.current || composing.current || draft.current) return;
    recovered.current = value;
    const next = { ...value, key: draftKey(value.scope, replica.current), updatedAt: Date.now() };
    await persist(next);
    draft.current = next;
    blocked.current = false;
    if (!base.current) {
      const offline: Copy = {
        branch: {
          id: value.scope.branch,
          artifact_id: artifact,
          name: "本机稿（联网后核对）",
          head_revision_id: value.baseRevision,
          version: value.version,
          document_epoch: value.epoch,
          editing_mode: "solo",
          archived: false,
        },
        revision: null,
        document: value.document,
        text: null,
        content_status: "local_only",
      };
      base.current = offline;
      setCopy(offline);
    }
    setDocument(next.document);
    setDirty(true);
    setConflict(null);
    setMessage("已恢复本机稿；同步时核对原基线");
    setError(null);
  }
  async function reconcile(choices: Choices) {
    if (!conflict || !draft.current) return;
    const local = draft.current;
    const result = await api.reconcile({
      base_revision_id: local.baseRevision,
      current_revision_id: conflict.remote.branch.head_revision_id ?? null,
      document: local.document,
      resolutions: choices,
    });
    if (draft.current?.changeId !== local.changeId)
      throw new Error("本机稿已改变，请重新核对冲突。");
    if (result.conflicts.length) {
      setConflict({ ...conflict, result });
      return;
    }
    const next: LocalDraft = {
      key: local.key,
      scope: local.scope,
      document: result.document,
      version: conflict.remote.branch.version,
      baseRevision: conflict.remote.branch.head_revision_id ?? null,
      epoch: conflict.remote.branch.document_epoch,
      changeId: crypto.randomUUID(),
      updatedAt: Date.now(),
    };
    await persist(next);
    draft.current = next;
    base.current = conflict.remote;
    setCopy(conflict.remote);
    setDocument(result.document);
    setConflict(null);
    blocked.current = false;
    setError(null);
  }
  return {
    api,
    copy,
    document,
    dirty,
    busy,
    error,
    message,
    recoveries,
    conflict,
    change,
    save,
    recover,
    reconcile,
    load,
    setError,
    resolving,
    retry: async () => {
      blocked.current = false;
      setError(null);
      await save();
    },
    onComposing: (value: boolean) => {
      composing.current = value;
      setIsComposing(value);
    },
    canChangeBranch: !dirty && !busy && !isComposing,
  };
}
