"use client";

import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";

import { cx } from "./utils.ts";

export interface TabItem {
  disabled?: boolean;
  id: string;
  label: string;
  panel: ReactNode;
}

export interface TabsProps {
  defaultValue?: string;
  label: string;
  onValueChange?: (value: string) => void;
  tabs: readonly TabItem[];
  value?: string;
}

export function Tabs({ defaultValue, label, onValueChange, tabs, value }: TabsProps) {
  const fallback = tabs.find((tab) => !tab.disabled)?.id ?? "";
  const [internalValue, setInternalValue] = useState(defaultValue ?? fallback);
  const activeValue = value ?? internalValue;
  const baseId = useId();
  const listRef = useRef<HTMLDivElement>(null);

  function select(id: string) {
    if (value === undefined) setInternalValue(id);
    onValueChange?.(id);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    const enabled = tabs.filter((tab) => !tab.disabled);
    if (enabled.length === 0) return;
    const currentIndex = enabled.findIndex((tab) => tab.id === activeValue);
    let nextIndex = currentIndex;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = enabled.length - 1;
    if (event.key === "ArrowRight")
      nextIndex = (currentIndex + 1 + enabled.length) % enabled.length;
    if (event.key === "ArrowLeft") nextIndex = (currentIndex - 1 + enabled.length) % enabled.length;
    const next = enabled[nextIndex];
    if (!next) return;
    event.preventDefault();
    select(next.id);
    listRef.current?.querySelector<HTMLElement>(`[data-tab-id="${CSS.escape(next.id)}"]`)?.focus();
  }

  return (
    <div className="ui-tabs">
      <div
        ref={listRef}
        aria-label={label}
        className="ui-tabs__list"
        onKeyDown={handleKeyDown}
        role="tablist"
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            aria-controls={`${baseId}-${tab.id}-panel`}
            aria-selected={activeValue === tab.id}
            className={cx("ui-tabs__tab", activeValue === tab.id && "ui-tabs__tab--active")}
            data-tab-id={tab.id}
            disabled={tab.disabled}
            id={`${baseId}-${tab.id}-tab`}
            onClick={() => {
              select(tab.id);
            }}
            role="tab"
            tabIndex={activeValue === tab.id ? 0 : -1}
            type="button"
          >
            {tab.label}
          </button>
        ))}
      </div>
      {tabs.map((tab) => (
        <div
          key={tab.id}
          aria-labelledby={`${baseId}-${tab.id}-tab`}
          className="ui-tabs__panel"
          hidden={activeValue !== tab.id}
          id={`${baseId}-${tab.id}-panel`}
          role="tabpanel"
          tabIndex={0}
        >
          {tab.panel}
        </div>
      ))}
    </div>
  );
}
