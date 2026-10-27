import type { components } from "@accos/api-client";

type Document = components["schemas"]["EditorDocument"];
export interface DraftScope {
  actor: string;
  workspace: string;
  project: string;
  artifact: string;
  branch: string;
}
export interface LocalDraft {
  key: string;
  scope: DraftScope;
  document: Document;
  baseRevision: string | null;
  version: number;
  epoch: number;
  changeId: string;
  updatedAt: number;
  pending?: { body: components["schemas"]["SaveContent"]; version: number };
}

function key(scope: DraftScope, replica: string) {
  return JSON.stringify([
    scope.actor,
    scope.workspace,
    scope.project,
    scope.artifact,
    scope.branch,
    replica,
  ]);
}
let database: Promise<IDBDatabase> | undefined;
function open(): Promise<IDBDatabase> {
  database ??= new Promise((resolve, reject) => {
    const request = indexedDB.open("accos-writing-v1", 1);
    request.onupgradeneeded = () => {
      request.result.createObjectStore("drafts", { keyPath: "key" });
    };
    request.onsuccess = () => {
      request.result.onversionchange = () => {
        request.result.close();
        database = undefined;
      };
      resolve(request.result);
    };
    request.onerror = () => {
      database = undefined;
      reject(request.error);
    };
    request.onblocked = () => {
      database = undefined;
      reject(new Error("本机草稿库被其他窗口占用"));
    };
  });
  return database;
}
async function transaction(mode: IDBTransactionMode, action: (store: IDBObjectStore) => void) {
  const db = await open();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction("drafts", mode);
    tx.oncomplete = () => {
      resolve();
    };
    tx.onerror = () => {
      reject(tx.error);
    };
    tx.onabort = () => {
      reject(tx.error ?? new Error("草稿写入中止"));
    };
    action(tx.objectStore("drafts"));
  });
}
export function draftKey(scope: DraftScope, replica: string) {
  return key(scope, replica);
}
export async function saveDraft(draft: LocalDraft) {
  await transaction("readwrite", (store) => {
    store.put(draft);
  });
  window.dispatchEvent(new Event("accos-drafts-changed"));
}
export async function removeDraft(draft: LocalDraft) {
  // An old save completion cannot erase a newer local edit.
  await transaction("readwrite", (store) => {
    const request = store.get(draft.key);
    request.onsuccess = () => {
      const stored = request.result as LocalDraft | undefined;
      if (stored?.changeId === draft.changeId) store.delete(draft.key);
    };
  });
  window.dispatchEvent(new Event("accos-drafts-changed"));
}
export async function localDrafts(actor: string): Promise<LocalDraft[]> {
  const result: LocalDraft[] = [];
  await transaction("readonly", (store) => {
    const request = store.openCursor();
    request.onsuccess = () => {
      const cursor = request.result;
      if (!cursor) return;
      const value = cursor.value as LocalDraft;
      if (value.scope.actor === actor) result.push(value);
      cursor.continue();
    };
  });
  return result.sort((a, b) => b.updatedAt - a.updatedAt);
}
export function sameScope(a: DraftScope, b: DraftScope) {
  return key(a, "") === key(b, "");
}
