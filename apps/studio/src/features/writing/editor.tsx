"use client";

import type { components } from "@accos/api-client";
import { useEffect, useRef } from "react";
import { Schema, type Node as PMNode } from "prosemirror-model";
import { EditorState, Plugin } from "prosemirror-state";
import { EditorView } from "prosemirror-view";
import { baseKeymap, setBlockType, toggleMark } from "prosemirror-commands";
import { history, redo, undo } from "prosemirror-history";
import { keymap } from "prosemirror-keymap";

export type Document = components["schemas"]["EditorDocument"];
const attrs = { id: { default: null }, locked: { default: false }, level: { default: 1 } };
export const editorSchema = new Schema({
  nodes: {
    doc: { content: "block*" },
    paragraph: {
      group: "block",
      content: "inline*",
      attrs,
      parseDOM: [{ tag: "p" }],
      toDOM: (node) => [
        "p",
        { "data-block-id": node.attrs.id, "data-locked": String(node.attrs.locked) },
        0,
      ],
    },
    heading: {
      group: "block",
      content: "inline*",
      attrs,
      parseDOM: [1, 2, 3].map((level) => ({ tag: `h${level}`, attrs: { level } })),
      toDOM: (node) => [
        `h${String(node.attrs.level)}`,
        { "data-block-id": node.attrs.id, "data-locked": String(node.attrs.locked) },
        0,
      ],
    },
    text: { group: "inline" },
    hard_break: {
      inline: true,
      group: "inline",
      selectable: false,
      parseDOM: [{ tag: "br" }],
      toDOM: () => ["br"],
    },
  },
  marks: {
    strong: { parseDOM: [{ tag: "strong" }, { tag: "b" }], toDOM: () => ["strong", 0] },
    em: { parseDOM: [{ tag: "em" }, { tag: "i" }], toDOM: () => ["em", 0] },
    code: { parseDOM: [{ tag: "code" }], toDOM: () => ["code", 0] },
  },
});

function documentJSON(node: PMNode): Document {
  return { ...node.toJSON(), schema_version: 1 } as Document;
}

export function emptyDocument(): Document {
  return {
    schema_version: 1,
    type: "doc",
    content: [
      {
        type: "paragraph",
        attrs: {
          id: crypto.randomUUID(),
          locked: false,
          level: 1,
        },
        content: [],
      },
    ],
  };
}

const stableBlocks = new Plugin({
  appendTransaction(transactions, _old, state) {
    if (!transactions.some((t) => t.docChanged)) return null;
    const seen = new Set<string>();
    const update = state.tr;
    state.doc.forEach((node, offset) => {
      const id = node.attrs.id as string | null;
      if (!id || seen.has(id))
        update.setNodeMarkup(offset, undefined, { ...node.attrs, id: crypto.randomUUID() });
      if (id) seen.add(id);
    });
    return update.docChanged ? update : null;
  },
  filterTransaction(transaction, state) {
    if (!transaction.docChanged || transaction.getMeta("toggle-lock")) return true;
    let valid = true;
    state.doc.forEach((node) => {
      if (!node.attrs.locked) return;
      let found = false;
      transaction.doc.forEach((next) => {
        if (next.attrs.id === node.attrs.id && next.eq(node)) found = true;
      });
      if (!found) valid = false;
    });
    return valid;
  },
});

export function ContentEditor({
  value,
  onChange,
  disabled,
  onComposing,
}: {
  value: Document;
  onChange: (document: Document) => void;
  disabled: boolean;
  onComposing: (value: boolean) => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const view = useRef<EditorView | null>(null);
  const callbacks = useRef({ onChange, onComposing, disabled });
  callbacks.current = { onChange, onComposing, disabled };
  useEffect(() => {
    if (!host.current) return;
    let compositionTimer: ReturnType<typeof setTimeout> | undefined;
    const initial = value.content?.length ? value : emptyDocument();
    const instance = new EditorView(host.current, {
      state: EditorState.create({
        schema: editorSchema,
        doc: editorSchema.nodeFromJSON(initial),
        plugins: [
          stableBlocks,
          history(),
          keymap({ "Mod-z": undo, "Mod-y": redo, "Mod-Shift-z": redo }),
          keymap(baseKeymap),
        ],
      }),
      editable: () => !callbacks.current.disabled,
      attributes: {
        "aria-label": "章节正文",
        role: "textbox",
        "aria-multiline": "true",
        spellcheck: "false",
      },
      dispatchTransaction(transaction) {
        const next = instance.state.applyTransaction(transaction);
        instance.updateState(next.state);
        if (next.transactions.some((t) => t.docChanged) && !instance.composing)
          callbacks.current.onChange(documentJSON(next.state.doc));
      },
      handleDOMEvents: {
        compositionstart: () => {
          callbacks.current.onComposing(true);
          return false;
        },
        compositionend: () => {
          compositionTimer = setTimeout(() => {
            callbacks.current.onComposing(false);
            callbacks.current.onChange(documentJSON(instance.state.doc));
          }, 50);
          return false;
        },
      },
    });
    view.current = instance;
    return () => {
      clearTimeout(compositionTimer);
      instance.destroy();
      view.current = null;
    };
    // The editor is keyed by document identity. External revisions are applied below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    const instance = view.current;
    if (!instance || instance.composing) return;
    const doc = editorSchema.nodeFromJSON(value.content?.length ? value : emptyDocument());
    if (!doc.eq(instance.state.doc)) {
      instance.updateState(
        EditorState.create({ schema: editorSchema, doc, plugins: instance.state.plugins }),
      );
    }
    instance.setProps({ editable: () => !disabled });
  }, [value, disabled]);
  function command(action: "bold" | "italic" | "paragraph" | "heading" | "lock" | "undo" | "redo") {
    const instance = view.current;
    if (!instance || disabled) return;
    const { state, dispatch } = instance;
    if (action === "bold" || action === "italic") {
      const mark = editorSchema.marks[action === "bold" ? "strong" : "em"];
      if (mark) toggleMark(mark)(state, dispatch);
    } else if (action === "undo") undo(state, dispatch);
    else if (action === "redo") redo(state, dispatch);
    else if (action === "lock") {
      const at = state.selection.$from;
      if (at.depth > 0)
        dispatch(
          state.tr
            .setNodeMarkup(at.before(1), undefined, {
              ...at.node(1).attrs,
              locked: !at.node(1).attrs.locked,
            })
            .setMeta("toggle-lock", true),
        );
    } else {
      const type = editorSchema.nodes[action];
      if (type)
        setBlockType(type, { id: state.selection.$from.parent.attrs.id, locked: false, level: 2 })(
          state,
          dispatch,
        );
    }
    instance.focus();
  }
  return (
    <div className="content-editor">
      <div className="studio-action-row" role="toolbar" aria-label="正文格式">
        {(
          [
            ["bold", "加粗"],
            ["italic", "斜体"],
            ["paragraph", "正文"],
            ["heading", "标题"],
            ["lock", "锁定／解锁本段"],
            ["undo", "撤销"],
            ["redo", "重做"],
          ] as const
        ).map(([action, label]) => (
          <button
            type="button"
            key={action}
            disabled={disabled}
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => command(action)}
          >
            {label}
          </button>
        ))}
      </div>
      <div ref={host} />
    </div>
  );
}
