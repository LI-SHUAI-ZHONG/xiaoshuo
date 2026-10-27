"""Stage-45 PostgreSQL/HTTP acceptance. Object double is explicit; real S3 is separate."""

from __future__ import annotations

import asyncio
import base64
import hashlib
from dataclasses import replace
from datetime import timedelta
from typing import Iterator
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
import test_identity_accounts_sql
from fastapi.testclient import TestClient
from sqlalchemy import select

from accos.adapters.assets.persistence import UploadSessionRow
from accos.adapters.assets.storage import InMemoryObjectStorage
from accos.adapters.persistence import DatabaseRuntime
from accos.composition import ApplicationContainer, build_container
from accos.entrypoints.api import create_app
from accos.kernel.auth_settings import AuthSettings
from accos.kernel.errors import ConcurrencyConflictError
from accos.kernel.ids import CorrelationIds
from accos.kernel.settings import RuntimeSettings
from accos.modules.identity.account_service import digest
from accos.modules.assets.public import object_key_for
from accos.modules.projects.content import SaveContent
from test_content_stage26 import block, doc

account_database = test_identity_accounts_sql.account_database


@pytest.fixture
def content_api(
    account_database: str, runtime_settings: RuntimeSettings, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[TestClient, ApplicationContainer, InMemoryObjectStorage, str, str]]:
    token = "stage26-bootstrap-" + uuid4().hex
    settings = replace(
        runtime_settings,
        required=replace(runtime_settings.required, database_url=account_database),
        auth=AuthSettings(
            bootstrap_digest=digest(token),
            secret_keys={"test": base64.urlsafe_b64encode(b"x" * 32).decode()},
            active_key_id="test",
        ),
    )
    storage = InMemoryObjectStorage()
    monkeypatch.setattr(
        DatabaseRuntime, "create", lambda url, options: DatabaseRuntime.create_unpooled(url)
    )
    monkeypatch.setattr("accos.composition.root.MinioObjectStorage", lambda **kwargs: storage)
    runtime = build_container(settings, probes=())
    client = TestClient(
        create_app(settings, container=runtime, configure_logs=False),
        base_url="http://localhost:3000",
    )
    client.headers["Origin"] = "http://localhost:3000"
    try:
        response = client.post(
            "/api/v1/auth/bootstrap",
            json={
                "username": "author",
                "password": "stage26-password-long",
                "bootstrap_token": token,
                "workspace_name": "正文隔离验收",
            },
        )
        assert response.status_code == 201
        info = response.json()
        workspace = info["workspaces"][0]["id"]
        client.headers.update({"X-Workspace-ID": workspace, "X-CSRF-Token": info["csrf_token"]})
        project = client.post(
            f"/api/v1/workspaces/{workspace}/projects",
            headers={"Idempotency-Key": str(uuid4())},
            json={"name": "正文验收"},
        )
        assert project.status_code == 201
        pid = project.json()["id"]
        artifact = client.post(
            f"/api/v1/projects/{pid}/artifacts",
            json={"label": "第一章", "artifact_type": "chapter"},
        )
        assert artifact.status_code == 201
        yield (
            client,
            runtime,
            storage,
            workspace,
            f"/api/v1/projects/{pid}/artifacts/{artifact.json()['id']}",
        )
    finally:
        client.close()
        asyncio.run(runtime.database.shutdown())


def save(client: TestClient, path: str, text: str, *, branch: str | None = None):
    copy = client.get(path + "/working-copy", params={"branch_id": branch} if branch else {}).json()
    change = str(uuid4())
    body = {
        "document": doc(block(1, text)).model_dump(mode="json"),
        "client_change_id": change,
        "base_revision_id": copy["branch"]["head_revision_id"],
        "document_epoch": copy["branch"]["document_epoch"],
    }
    headers = {"If-Match": f'"{copy["branch"]["version"]}"', "Idempotency-Key": change}
    response = client.put(
        path + "/working-copy",
        json=body,
        headers=headers,
        params={"branch_id": copy["branch"]["id"]},
    )
    assert response.status_code == 200, response.text
    return response.json(), body, headers


@pytest.mark.integration
def test_t011_t012_t013_commit_replay_cas_restore_and_restart(content_api) -> None:
    client, runtime, _storage, _workspace, path = content_api
    first, body, headers = save(client, path, "第一版中文🙂")
    replay = client.put(path + "/working-copy", json=body, headers=headers)
    assert replay.status_code == 200 and replay.json()["id"] == first["id"]
    assert (
        client.put(
            path + "/working-copy",
            json={**body, "document": doc(block(1, "changed")).model_dump(mode="json")},
            headers=headers,
        ).status_code
        == 409
    )
    second, _, _ = save(client, path, "第二版")
    third, _, _ = save(client, path, "第三版")
    stale = {**body, "client_change_id": str(uuid4())}
    assert (
        client.put(
            path + "/working-copy",
            json=stale,
            headers={**headers, "Idempotency-Key": stale["client_change_id"]},
        ).status_code
        == 409
    )
    assert (
        client.put(
            path + "/working-copy", json=body, headers={"Idempotency-Key": body["client_change_id"]}
        ).status_code
        == 428
    )
    change = str(uuid4())
    restored = client.post(
        path + f"/revisions/{first['id']}/restore",
        json={
            "branch_id": third["branch_id"],
            "base_revision_id": third["id"],
            "document_epoch": 1,
            "client_change_id": change,
        },
        headers={"If-Match": '"3"', "Idempotency-Key": change},
    )
    assert restored.status_code == 200
    assert restored.json()["revision_number"] == 4
    assert set(restored.json()["parents"]) == {third["id"], first["id"]}
    original = client.get(path + "/content", params={"revision_id": first["id"]}).json()
    assert (
        original["text"] == "第一版中文🙂"
        and original["revision"]["content_hash"] == first["content_hash"]
    )
    assert second["id"] != restored.json()["id"]
    # New repository objects read durable state, not an in-memory revision cache.
    from accos.adapters.projects.content import SqlAlchemyContentRepository

    fresh = SqlAlchemyContentRepository(runtime.database.sessions)
    head = asyncio.run(
        fresh.head(
            UUID(first["workspace_id"]),
            UUID(first["project_id"]),
            UUID(first["artifact_id"]),
            UUID(first["branch_id"]),
        )
    )
    assert str(head.head_revision_id) == restored.json()["id"]
    legacy = client.post(
        path + "/revisions",
        json={"content_reference": "studio-input://old", "content_hash": "a" * 64},
        headers={"If-Match": '"5"'},
    )
    assert legacy.status_code == 409


@pytest.mark.integration
def test_t014_branch_conflict_merge_and_patch_preserve_author(content_api) -> None:
    client, _runtime, _storage, _workspace, path = content_api
    base, _, _ = save(client, path, "初稿")
    branch = client.post(
        path + "/branches",
        json={"name": "试写", "base_revision_id": base["id"]},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert branch.status_code == 201
    ours, _, _ = save(client, path, "作者版本")
    theirs, _, _ = save(client, path, "分支版本", branch=branch.json()["id"])
    comparison = client.get(path + "/diffs", params={"ours": ours["id"], "theirs": theirs["id"]})
    assert comparison.status_code == 200 and len(comparison.json()["conflicts"]) == 1
    change = str(uuid4())
    body = {
        "branch_id": ours["branch_id"],
        "base_revision_id": ours["id"],
        "source_revision_id": theirs["id"],
        "document_epoch": 1,
        "client_change_id": change,
        "resolutions": {},
    }
    headers = {"If-Match": '"2"', "Idempotency-Key": change}
    assert client.post(path + "/merge", json=body, headers=headers).status_code == 409
    merged = client.post(
        path + "/merge", json={**body, "resolutions": {str(UUID(int=1)): "ours"}}, headers=headers
    )
    assert merged.status_code == 200 and set(merged.json()["parents"]) == {ours["id"], theirs["id"]}
    candidate = client.post(
        path + "/patches",
        json={
            "branch_id": ours["branch_id"],
            "base_revision_id": base["id"],
            "document": doc(block(1, "旧基线候选")).model_dump(mode="json"),
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert candidate.status_code == 201
    patch_change = str(uuid4())
    applied = client.post(
        path + f"/patches/{candidate.json()['id']}/apply",
        json={
            "branch_id": ours["branch_id"],
            "base_revision_id": merged.json()["id"],
            "document_epoch": 1,
            "client_change_id": patch_change,
            "resolutions": {},
        },
        headers={"If-Match": '"3"', "Idempotency-Key": patch_change},
    )
    assert applied.status_code == 409
    assert client.get(path + "/working-copy").json()["text"] == "作者版本"


@pytest.mark.integration
def test_t011_t015_storage_failure_never_commits_pointer(
    content_api, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _runtime, storage, _workspace, path = content_api
    monkeypatch.setattr(storage, "put", AsyncMock(side_effect=OSError("isolated failure")))
    change = str(uuid4())
    response = client.put(
        path + "/working-copy",
        json={
            "document": doc(block(1, "不能假报成功")).model_dump(mode="json"),
            "base_revision_id": None,
            "document_epoch": 1,
            "client_change_id": change,
        },
        headers={"If-Match": '"0"', "Idempotency-Key": change},
    )
    assert response.status_code == 503
    assert client.get(path + "/working-copy").json()["branch"]["version"] == 0
    assert client.get(path + "/revision-history").json()["items"] == []


@pytest.mark.integration
def test_t015_t016_download_authorization_catalog_and_archive(content_api) -> None:
    client, _runtime, _storage, workspace, path = content_api
    revision, _, _ = save(client, path, "归档前的正文")
    pid = revision["project_id"]
    ref = revision["document_ref"]
    asset_path = (
        f"/api/v1/projects/{pid}/assets/{ref['asset_id']}/versions/{ref['asset_version_id']}"
    )
    ticket = client.post(asset_path + "/download-ticket")
    assert ticket.status_code == 200
    content = client.get(ticket.json()["url"])
    assert (
        content.status_code == 200 and hashlib.sha256(content.content).hexdigest() == ref["sha256"]
    )
    assert "attachment" in content.headers["content-disposition"]
    assert (
        client.get(ticket.json()["url"], headers={"X-Workspace-ID": str(uuid4())}).status_code
        == 403
    )
    assert client.get(asset_path + "/content?ticket=bad").status_code == 403
    page = client.get(
        f"/api/v1/workspaces/{workspace}/projects/page", params={"query": "正文"}
    ).json()
    assert page["items"][0]["id"] == pid
    assert (
        client.put(
            f"/api/v1/projects/{pid}/details",
            json={"name": "归档稿", "archived": True},
            headers={"If-Match": '"1"'},
        ).status_code
        == 200
    )
    assert client.get(path + "/working-copy").json()["text"] == "归档前的正文"
    assert not client.get(f"/api/v1/workspaces/{workspace}/projects/page").json()["items"]
    assert (
        client.get(f"/api/v1/workspaces/{workspace}/projects/page?archived=true").json()["items"][
            0
        ]["id"]
        == pid
    )
    assert (
        client.put(
            f"/api/v1/projects/{pid}/details",
            json={"name": "归档稿", "archived": False},
            headers={"If-Match": '"2"'},
        ).status_code
        == 200
    )


@pytest.mark.integration
def test_t015_orphan_collection_keeps_registered_and_held_objects(content_api) -> None:
    client, runtime, storage, workspace, path = content_api
    revision, _, _ = save(client, path, "保留中")

    async def collect() -> None:
        async with runtime.database.sessions() as session:
            original = await session.scalar(
                select(UploadSessionRow).where(UploadSessionRow.workspace_id == UUID(workspace))
            )
            assert original is not None
            values = {
                column.name: getattr(original, column.name)
                for column in UploadSessionRow.__table__.columns
            }
        abandoned: list[tuple[UUID, str]] = []
        async with runtime.database.sessions.begin() as session:
            for _ in range(2):
                identifier = uuid4()
                key = original.object_key.rsplit("/", 1)[0] + "/" + str(uuid4())
                await storage.put(
                    key,
                    b"orphan",
                    media_type="text/plain",
                    content_hash=hashlib.sha256(b"orphan").hexdigest(),
                )
                session.add(
                    UploadSessionRow(
                        **{
                            **values,
                            "id": identifier,
                            "asset_id": uuid4(),
                            "asset_version_id": uuid4(),
                            "object_key": key,
                            "status": "failed",
                            "updated_at": original.updated_at - timedelta(days=31),
                            "error_code": "failed",
                        }
                    )
                )
                abandoned.append((identifier, key))
        await runtime.assets.orphan_collector.hold(
            UUID(workspace), abandoned[0][0], "backup:stage45"
        )
        assert await runtime.assets.orphan_collector.run_once() == 1
        assert await storage.stat(abandoned[0][1]) is not None
        assert await storage.stat(abandoned[1][1]) is None
        assert await storage.stat(original.object_key) is not None

    asyncio.run(collect())
    assert (
        client.get(path + "/content", params={"revision_id": revision["id"]}).json()["text"]
        == "保留中"
    )


@pytest.mark.integration
def test_t011_verified_legacy_import_preserves_the_original_record(content_api) -> None:
    client, runtime, _storage, workspace, path = content_api
    pid = path.split("/")[4]
    data = "来自旧对象的中文\n".encode()
    content_hash = hashlib.sha256(data).hexdigest()
    uploaded = client.post(
        f"/api/v1/projects/{pid}/assets",
        json={
            "filename": "legacy.txt",
            "media_type": "text/plain",
            "content_base64": base64.b64encode(data).decode(),
            "expected_sha256": content_hash,
        },
    )
    assert uploaded.status_code == 201
    asset = uploaded.json()
    version = asset["current"]
    key = object_key_for(UUID(workspace), UUID(pid), UUID(asset["id"]), UUID(version["id"]))
    reference = f"s3://{runtime.settings.required.s3_bucket}/{key}"
    old = client.post(
        path + "/revisions",
        json={"content_reference": reference, "content_hash": content_hash},
        headers={"If-Match": '"1"'},
    )
    assert old.status_code == 201
    copy = client.get(path + "/working-copy").json()
    assert copy["content_status"] == "legacy_unverified" and copy["document"] is None
    change = str(uuid4())
    body = {
        "branch_id": copy["branch"]["id"],
        "base_revision_id": old.json()["id"],
        "document_epoch": 1,
        "client_change_id": change,
        "source_asset": {
            "asset_id": asset["id"],
            "asset_version_id": version["id"],
            "sha256": content_hash,
            "media_type": "text/plain",
            "byte_length": len(data),
        },
    }
    imported = client.post(
        path + f"/revisions/{old.json()['id']}/import-legacy",
        json=body,
        headers={"If-Match": '"0"', "Idempotency-Key": change},
    )
    assert imported.status_code == 200
    assert client.get(path + "/working-copy").json()["text"].encode() == data
    original = client.get(path + "/content", params={"revision_id": old.json()["id"]}).json()
    assert original["revision"]["content_reference"] == reference
    assert original["revision"]["content_hash"] == content_hash and original["document"] is None


@pytest.mark.integration
def test_t012_two_simultaneous_writers_commit_exactly_one_revision(content_api) -> None:
    client, runtime, _storage, workspace, path = content_api
    copy = client.get(path + "/working-copy").json()
    pid, aid = UUID(path.split("/")[4]), UUID(path.split("/")[6])

    async def race() -> None:
        ctx = await runtime.identity.authenticator.authenticate(
            client.cookies.get("accos_session"),
            UUID(workspace),
            CorrelationIds(str(uuid4()), str(uuid4())),
        )
        results = await asyncio.gather(
            *(
                runtime.projects.content.save(
                    ctx,
                    pid,
                    aid,
                    UUID(copy["branch"]["id"]),
                    SaveContent(
                        document=doc(block(1, text)),
                        client_change_id=uuid4(),
                        base_revision_id=None,
                        document_epoch=1,
                    ),
                    0,
                )
                for text in ("同时写入甲", "同时写入乙")
            ),
            return_exceptions=True,
        )
        assert sum(isinstance(result, ConcurrencyConflictError) for result in results) == 1
        assert sum(not isinstance(result, BaseException) for result in results) == 1

    asyncio.run(race())
    history = client.get(path + "/revision-history").json()["items"]
    assert len(history) == 1
    assert client.get(path + "/working-copy").json()["text"] in {"同时写入甲", "同时写入乙"}
