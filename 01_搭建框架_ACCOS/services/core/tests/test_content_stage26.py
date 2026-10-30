"""T011/T014/T015 pure contract cases, registered for stage 45; not run in construction."""

from __future__ import annotations

import asyncio
import base64
import hashlib
from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from accos.kernel.auth_settings import AuthSettings
from accos.kernel.errors import InvalidRequestError, InvalidStateError, PermissionDeniedError
from accos.modules.assets.application import _validate_media
from accos.modules.assets.downloads import VersionDownloadSigner
from accos.modules.identity.domain import Role
from accos.modules.projects.content import (
    BlockAttributes,
    EditorBlock,
    EditorDocument,
    HardBreak,
    TextNode,
    merge_documents,
    require_unlocked_patch,
)
from test_projects_assets import NOW, FixedClock, context


def block(number: int, text: str, *, locked: bool = False) -> EditorBlock:
    return EditorBlock(
        attrs=BlockAttributes(id=UUID(int=number), locked=locked),
        content=(TextNode(text=text),) if text else (),
    )


def doc(*blocks: EditorBlock) -> EditorDocument:
    return EditorDocument(content=blocks)


def test_t011_canonical_unicode_projection_empty_and_unique_ids() -> None:
    value = doc(
        block(1, "中文🙂"),
        EditorBlock(
            attrs=BlockAttributes(id=UUID(int=2)),
            content=(TextNode(text="换行"), HardBreak(), TextNode(text="末尾")),
        ),
    )
    assert value.plain_text() == "中文🙂\n换行\n末尾"
    parsed = EditorDocument.model_validate_json(value.to_bytes())
    assert parsed == value and parsed.digest() == hashlib.sha256(value.to_bytes()).hexdigest()
    assert doc().plain_text() == ""
    with pytest.raises(ValidationError):
        doc(block(1, "first"), block(1, "duplicate"))
    with pytest.raises(ValidationError):
        doc(block(1, "bad\x00text"))


def test_t014_disjoint_edits_insert_delete_and_conflicts_retain_both() -> None:
    base = doc(block(1, "第一段"), block(2, "第二段"))
    ours = doc(block(1, "作者修改"), block(2, "第二段"))
    theirs = doc(block(1, "第一段"), block(2, "分支修改"), block(3, "新增"))
    merged = merge_documents(base, ours, theirs)
    assert not merged.conflicts
    assert merged.document.plain_text() == "作者修改\n分支修改\n新增"
    collision = merge_documents(base, ours, doc(block(1, "另一改稿")))
    assert len(collision.conflicts) == 1
    assert collision.conflicts[0].ours == block(1, "作者修改")
    assert collision.conflicts[0].theirs == block(1, "另一改稿")
    resolved = merge_documents(base, ours, doc(block(1, "另一改稿")), {str(UUID(int=1)): "theirs"})
    assert not resolved.conflicts and resolved.document.plain_text() == "另一改稿"
    with pytest.raises(InvalidRequestError):
        merge_documents(base, ours, theirs, {str(uuid4()): "ours"})


def test_t014_reordering_and_candidate_locks_are_explicit() -> None:
    a, b, c = block(1, "a"), block(2, "b"), block(3, "c")
    conflict = merge_documents(doc(a, b, c), doc(b, a, c), doc(a, c, b))
    assert conflict.conflicts[0].reason == "incompatible_order"
    resolved = merge_documents(doc(a, b, c), doc(b, a, c), doc(a, c, b), {"__order__": "theirs"})
    assert resolved.document.content == (a, c, b)
    with pytest.raises(InvalidStateError):
        require_unlocked_patch(doc(block(1, "锁定", locked=True)), doc(block(1, "覆盖")))
    protected = merge_documents(
        doc(a), doc(block(1, "作者锁定", locked=True)), doc(block(1, "旧候选")), protect_locks=True
    )
    assert protected.document == doc(block(1, "作者锁定", locked=True))


@pytest.mark.parametrize(
    "data,media",
    [
        (b"not a png", "image/png"),
        (b"%notpdf", "application/pdf"),
        (b"not-json", "application/json"),
        (b"bad\x00text", "text/plain"),
        (b"not a zip", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ],
)
def test_t015_mime_spoofing_is_rejected(data: bytes, media: str) -> None:
    with pytest.raises(InvalidRequestError):
        _validate_media(data, media)


def test_t015_signed_download_binds_actor_scope_version_and_expiry() -> None:
    config = AuthSettings(
        secret_keys={"test": base64.urlsafe_b64encode(b"x" * 32).decode()}, active_key_id="test"
    )
    signer = VersionDownloadSigner(config, FixedClock())
    actor = context(Role.OWNER)
    project, asset, version = uuid4(), uuid4(), uuid4()
    ticket = signer.issue(actor, project, asset, version)
    signer.verify(ticket, actor, project, asset, version)
    for token in ("bad", "!.bad", ticket + "tampered"):
        with pytest.raises(PermissionDeniedError):
            signer.verify(token, actor, project, asset, version)
    with pytest.raises(PermissionDeniedError):
        signer.verify(ticket, replace(actor, actor_id=uuid4()), project, asset, version)
    with pytest.raises(PermissionDeniedError):
        signer.verify(ticket, actor, project, asset, uuid4())

    class Later:
        def now(self):
            return NOW + timedelta(minutes=6)

    with pytest.raises(PermissionDeniedError):
        VersionDownloadSigner(config, Later()).verify(ticket, actor, project, asset, version)


def test_t015_empty_plaintext_is_a_valid_projection() -> None:
    _validate_media(b"", "text/plain")
    from accos.modules.assets.application import DefaultUploadSecurityPolicy
    from accos.modules.identity.public import UploadDescriptor

    assert asyncio.run(
        DefaultUploadSecurityPolicy().permits(
            context(Role.OWNER), UploadDescriptor("text/plain", 0, "projection.txt")
        )
    )
