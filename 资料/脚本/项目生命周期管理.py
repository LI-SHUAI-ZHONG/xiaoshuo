"""保守管理小说项目的创建、注册和归档边界。"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REGISTRY_RELATIVE_PATH = Path("配置") / "项目注册表.json"
ARCHIVE_RELATIVE_PATH = Path("归档") / "项目"
LOCK_RELATIVE_PATH = Path("配置") / ".项目生命周期.lock"
ARCHIVE_TRANSACTION_RELATIVE_PATH = Path("归档") / "项目归档事务.json"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_registry(workspace_root: Path) -> dict[str, Any]:
    path = workspace_root / REGISTRY_RELATIVE_PATH
    if not path.is_file():
        return {"schema_version": "project-registry-1.0", "projects": []}
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"项目注册表不可解析：{path}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("projects", []), list):
        raise ValueError("项目注册表格式错误")
    return value


def _save_registry(workspace_root: Path, registry: dict[str, Any]) -> None:
    path = workspace_root / REGISTRY_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _acquire_lock(workspace_root: Path) -> int:
    path = workspace_root / LOCK_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        return os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
    except FileExistsError as exc:
        raise ValueError("项目生命周期操作正在进行，拒绝并发修改") from exc


def _release_lock(workspace_root: Path, descriptor: int) -> None:
    os.close(descriptor)
    (workspace_root / LOCK_RELATIVE_PATH).unlink(missing_ok=True)


def _normalized_project_path(value: Any) -> str:
    text = str(value or "").strip()
    return str(Path(text).expanduser().resolve()) if text else ""


def validate_new_project_root(workspace_root: str | Path, project_root: str | Path, book_title: str = "") -> None:
    """拒绝非 ``作品/<书名>`` 直接子目录、已知项目和归档书名复用。"""
    workspace = Path(workspace_root).expanduser().resolve()
    root = Path(project_root).expanduser().resolve()
    if root.parent != (workspace / "作品").resolve() or not root.name.strip():
        raise ValueError("直接子目录 required: new project root must be a direct 作品/<book> child")
    registry = _load_registry(workspace)
    normalized_title = book_title.strip() or root.name
    for item in registry["projects"]:
        if not isinstance(item, dict):
            continue
        item_root = _normalized_project_path(item.get("project_root"))
        if item.get("status") == "archived" and (item.get("book_title") == normalized_title or item_root == str(root)):
            raise ValueError("书名已归档，禁止重新启动")
        if item.get("book_title") == normalized_title or item_root == str(root):
            raise ValueError("书名或项目目录已注册，禁止重新启动")
    archive_root = workspace / ARCHIVE_RELATIVE_PATH
    if archive_root.is_dir() and any(path.name == normalized_title for path in archive_root.iterdir()):
        raise ValueError("书名已归档，禁止重新启动")
    if root.exists() and any(root.iterdir()):
        raise ValueError("目标项目目录已有不可识别资料，拒绝初始化")


def register_project(
    workspace_root: str | Path,
    project_root: str | Path,
    project_id: str,
    book_title: str = "",
    resource_root: str | Path | None = None,
) -> dict[str, Any]:
    workspace = Path(workspace_root).expanduser().resolve()
    root = Path(project_root).expanduser().resolve()
    if root.parent != (workspace / "作品").resolve() or not root.name.strip() or not root.is_dir():
        raise ValueError("注册项目目录必须是正式根下的作品/<书名>目录")
    normalized_id = str(project_id or "").strip()
    normalized_title = book_title.strip() or root.name
    if not normalized_id:
        raise ValueError("project_id 不能为空")
    descriptor = _acquire_lock(workspace)
    try:
        registry = _load_registry(workspace)
        for item in registry["projects"]:
            if not isinstance(item, dict):
                continue
            item_root = _normalized_project_path(item.get("project_root"))
            same_root = item_root == str(root)
            same_id = str(item.get("project_id") or "") == normalized_id
            same_title = str(item.get("book_title") or "") == normalized_title
            if same_root and same_id and same_title and item.get("status") == "active":
                return item
            if same_id:
                raise ValueError("project_id 已注册到其他项目")
            if same_root or same_title:
                raise ValueError("书名或项目目录已注册，禁止重复注册")
        record = {
            "project_id": normalized_id,
            "book_title": normalized_title,
            "project_root": str(root),
            "resource_root": str(Path(resource_root).expanduser().resolve()) if resource_root else str(workspace),
            "status": "active",
            "registered_at": _now(),
        }
        registry["projects"].append(record)
        registry["updated_at"] = _now()
        _save_registry(workspace, registry)
        return record
    finally:
        _release_lock(workspace, descriptor)


def validate_active_project(
    workspace_root: str | Path,
    project_root: str | Path,
    project_id: str | None = None,
    book_title: str | None = None,
    resource_root: str | Path | None = None,
) -> dict[str, Any]:
    workspace = Path(workspace_root).expanduser().resolve()
    root = Path(project_root).expanduser().resolve()
    registry = _load_registry(workspace)
    record = next(
        (
            item for item in registry["projects"]
            if isinstance(item, dict) and _normalized_project_path(item.get("project_root")) == str(root)
        ),
        None,
    )
    if not isinstance(record, dict) or record.get("status") != "active":
        raise ValueError("项目未登记或不是 active 项目")
    if project_id and str(record.get("project_id")) != str(project_id):
        raise ValueError("项目注册表 project_id 与当前项目不一致")
    if book_title and str(record.get("book_title")) != str(book_title):
        raise ValueError("项目注册表书名与当前项目不一致")
    if resource_root and _normalized_project_path(record.get("resource_root")) != str(Path(resource_root).expanduser().resolve()):
        raise ValueError("项目注册表 resource_root 与当前项目不一致")
    return record


def list_projects(workspace_root: str | Path) -> list[dict[str, Any]]:
    return [
        item for item in _load_registry(Path(workspace_root).expanduser().resolve())["projects"]
        if isinstance(item, dict)
    ]


def _file_manifest(root: Path) -> list[dict[str, str]]:
    result = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        result.append({"relative_path": path.relative_to(root).as_posix(), "sha256": digest})
    return result


def archive_project(workspace_root: str | Path, project_root: str | Path) -> Path:
    workspace = Path(workspace_root).expanduser().resolve()
    root = Path(project_root).expanduser().resolve()
    descriptor = _acquire_lock(workspace)
    transaction_path = workspace / ARCHIVE_TRANSACTION_RELATIVE_PATH
    try:
        registry = _load_registry(workspace)
        record = next(
            (
                item for item in registry["projects"]
                if isinstance(item, dict) and _normalized_project_path(item.get("project_root")) == str(root)
            ),
            None,
        )
        if record is None:
            raise ValueError("项目未注册，拒绝归档")
        if record.get("status") != "active":
            raise ValueError("只有 active 项目允许归档")
        archive = workspace / ARCHIVE_RELATIVE_PATH / root.name
        if archive.exists():
            raise ValueError("归档目标已存在")
        transaction = {
            "schema_version": "project-archive-transaction-1.0",
            "status": "prepared",
            "project_id": record["project_id"],
            "project_root": str(root),
            "archive_root": str(archive),
            "started_at": _now(),
        }
        transaction_path.parent.mkdir(parents=True, exist_ok=True)
        transaction_path.write_text(json.dumps(transaction, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        record["status"] = "archiving"
        registry["updated_at"] = _now()
        _save_registry(workspace, registry)
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(root, archive)
        manifest = {
            "schema_version": "project-archive-manifest-1.0",
            "project_id": record["project_id"],
            "archived_at": _now(),
            "files": _file_manifest(archive),
        }
        (archive / "归档文件哈希清单.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for path in archive.rglob("*"):
            if path.is_file():
                path.chmod(0o444)
        archive.chmod(0o555)
        record["status"] = "archived"
        record["archive_root"] = str(archive)
        record["archived_at"] = manifest["archived_at"]
        registry["updated_at"] = _now()
        _save_registry(workspace, registry)
        transaction.update({"status": "completed", "completed_at": _now()})
        transaction_path.write_text(json.dumps(transaction, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return archive
    finally:
        _release_lock(workspace, descriptor)
