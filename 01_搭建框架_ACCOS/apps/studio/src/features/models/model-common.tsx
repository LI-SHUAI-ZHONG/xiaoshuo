"use client";

import Link from "next/link";
import { useState, type TextareaHTMLAttributes } from "react";
import { useIdentity } from "../../providers/identity-provider";

export function useModelOwner() {
  const identity = useIdentity();
  return (
    identity.permissions.includes("membership:manage") &&
    ["local", "oidc"].includes(identity.auth_method)
  );
}

export function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  async function run(work: () => Promise<void>, success = "操作已保存。") {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await work();
      setMessage(success);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "操作失败，请重试。");
    } finally {
      setBusy(false);
    }
  }
  return {
    busy,
    run,
    notice: (
      <>
        {error ? <p role="alert">{error}</p> : null}
        {message ? <p role="status">{message}</p> : null}
      </>
    ),
  };
}

export function TextArea({
  label,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string }) {
  return (
    <label className="ui-field">
      <span className="ui-field__label">{label}</span>
      <textarea className="ui-input model-textarea" {...props} />
    </label>
  );
}

export function ModelNavigation() {
  return (
    <nav aria-label="模型设置" className="studio-project-nav">
      <Link href="/settings">工作区与密钥</Link>
      <Link href="/settings/models">模型与预算</Link>
      <Link href="/settings/prompts">Prompt 版本</Link>
    </nav>
  );
}

export function objectJson(value: string): Record<string, unknown> {
  const parsed: unknown = JSON.parse(value);
  if (!parsed || Array.isArray(parsed) || typeof parsed !== "object")
    throw new Error("请填写 JSON 对象。");
  return parsed as Record<string, unknown>;
}

export const pretty = (value: unknown) => JSON.stringify(value, null, 2);
