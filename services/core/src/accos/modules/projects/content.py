"""Versioned ProseMirror documents, immutable revision references and block merges."""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal, Self
from uuid import UUID, uuid5

from pydantic import AwareDatetime, Field, model_validator

from accos.kernel.errors import InvalidRequestError, InvalidStateError
from accos.kernel.shared_contracts import ContentRef, SharedContract


class TextMark(SharedContract):
    type: Literal["strong", "em", "code"]


class TextNode(SharedContract):
    type: Literal["text"] = "text"
    text: str = Field(min_length=1, max_length=2_000_000)
    marks: tuple[TextMark, ...] = ()


class HardBreak(SharedContract):
    type: Literal["hard_break"] = "hard_break"


class BlockAttributes(SharedContract):
    id: UUID
    locked: bool = False
    level: int = Field(default=1, ge=1, le=3)


class EditorBlock(SharedContract):
    type: Literal["paragraph", "heading"] = "paragraph"
    attrs: BlockAttributes
    content: tuple[Annotated[TextNode | HardBreak, Field(discriminator="type")], ...] = ()


class EditorDocument(SharedContract):
    schema_version: Literal[1] = 1
    type: Literal["doc"] = "doc"
    content: tuple[EditorBlock, ...] = Field(default=(), max_length=50_000)

    @model_validator(mode="after")
    def unique_blocks(self) -> Self:
        if len({block.attrs.id for block in self.content}) != len(self.content):
            raise ValueError("Every document block needs a unique stable ID")
        if len(self.to_bytes()) > 8 * 1024 * 1024:
            raise ValueError("Document exceeds the 8 MiB snapshot limit")
        if any(
            "\x00" in node.text
            for block in self.content
            for node in block.content
            if isinstance(node, TextNode)
        ):
            raise ValueError("Document text cannot contain NUL characters")
        return self

    def to_bytes(self) -> bytes:
        return json.dumps(
            self.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")

    def plain_text(self) -> str:
        return "\n".join(
            "".join(node.text if isinstance(node, TextNode) else "\n" for node in block.content)
            for block in self.content
        )

    def digest(self) -> str:
        return hashlib.sha256(self.to_bytes()).hexdigest()


def main_branch(artifact_id: UUID) -> UUID:
    return uuid5(artifact_id, "accos-main-branch-v1")


class ContentRevision(SharedContract):
    id: UUID
    workspace_id: UUID
    project_id: UUID
    artifact_id: UUID
    revision_number: int
    branch_id: UUID | None
    content_status: Literal["available", "empty", "legacy_content_unavailable", "legacy_unverified"]
    document_ref: ContentRef | None = None
    text_ref: ContentRef | None = None
    content_hash: str | None = None
    content_reference: str | None = None
    editor_schema_version: int | None = None
    parents: tuple[UUID, ...] = ()
    operation: str = "legacy"
    created_by: UUID
    created_at: AwareDatetime
    working_version: int = 0
    document_epoch: int = 1


class Branch(SharedContract):
    id: UUID
    artifact_id: UUID
    name: str
    head_revision_id: UUID | None = None
    version: int = 0
    document_epoch: int = 1
    editing_mode: Literal["solo", "collaborative"] = "solo"
    archived: bool = False


class WorkingCopy(SharedContract):
    branch: Branch
    revision: ContentRevision | None
    document: EditorDocument | None
    text: str | None
    content_status: str


class SaveContent(SharedContract):
    document: EditorDocument
    client_change_id: UUID
    base_revision_id: UUID | None
    document_epoch: int = Field(ge=1)


class MergeConflict(SharedContract):
    block_id: str
    base: EditorBlock | None = None
    ours: EditorBlock | None = None
    theirs: EditorBlock | None = None
    reason: str = "both_changed"


class MergeResult(SharedContract):
    document: EditorDocument
    conflicts: tuple[MergeConflict, ...]
    differences: tuple[MergeConflict, ...] = ()
    order_changed: bool = False


def merge_documents(
    base: EditorDocument,
    ours: EditorDocument,
    theirs: EditorDocument,
    resolutions: dict[str, Literal["ours", "theirs"]] | None = None,
    *,
    protect_locks: bool = False,
) -> MergeResult:
    """Merge stable blocks; incompatible reorderings remain explicit conflicts."""
    choices = resolutions or {}
    maps = [{str(b.attrs.id): b for b in doc.content} for doc in (base, ours, theirs)]
    before, left, right = maps
    merged: dict[str, EditorBlock] = {}
    conflicts: list[MergeConflict] = []
    for identifier in dict.fromkeys((*before, *left, *right)):
        b, o, t = before.get(identifier), left.get(identifier), right.get(identifier)
        value: EditorBlock | None
        if protect_locks and o is not None and o.attrs.locked:
            value = o
        elif o == t or t == b:
            value = o
        elif o == b:
            value = t
        elif identifier in choices:
            value = o if choices[identifier] == "ours" else t
        else:
            conflicts.append(MergeConflict(block_id=identifier, base=b, ours=o, theirs=t))
            value = o
        if value is not None:
            merged[identifier] = value
    # Only changed ordering imposes new constraints. Unchanged sides do not undo a move.
    common = set(before) & set(left) & set(right)
    original = [k for k in before if k in common]
    lorder = [k for k in left if k in common]
    rorder = [k for k in right if k in common]
    order_conflict = lorder != original and rorder != original and lorder != rorder
    selected = right if lorder == original and rorder != original else left
    if order_conflict:
        if "__order__" not in choices:
            conflicts.append(MergeConflict(block_id="__order__", reason="incompatible_order"))
        selected = right if choices.get("__order__") == "theirs" else left
    ordered = [k for k in selected if k in merged]
    other = left if selected is right else right
    other_keys = list(other)
    for index, key in enumerate(other_keys):
        if key not in merged or key in ordered:
            continue
        preceding = next((k for k in reversed(other_keys[:index]) if k in ordered), None)
        following = next((k for k in other_keys[index + 1 :] if k in ordered), None)
        if preceding is not None:
            ordered.insert(ordered.index(preceding) + 1, key)
        elif following is not None:
            ordered.insert(ordered.index(following), key)
        else:
            ordered.append(key)
    if set(choices) - {*(str(k) for k in before), *left, *right, "__order__"}:
        raise InvalidRequestError("Resolution names an unknown block.")
    differences = tuple(
        MergeConflict(
            block_id=k,
            base=before.get(k),
            ours=left.get(k),
            theirs=right.get(k),
            reason="added" if k not in left else "removed" if k not in right else "changed",
        )
        for k in dict.fromkeys((*left, *right))
        if left.get(k) != right.get(k)
    )
    return MergeResult(
        document=EditorDocument(content=tuple(merged[k] for k in ordered)),
        conflicts=tuple(conflicts),
        differences=differences,
        order_changed=lorder != rorder,
    )


def require_unlocked_patch(base: EditorDocument, candidate: EditorDocument) -> None:
    blocks = {b.attrs.id: b for b in candidate.content}
    for block in base.content:
        if block.attrs.locked and blocks.get(block.attrs.id) != block:
            raise InvalidStateError("Candidate patches cannot alter locked blocks.")
