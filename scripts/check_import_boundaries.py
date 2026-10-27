"""Enforce dependency rules that are more specific than Import Linter contracts."""

from __future__ import annotations

import ast
import sys
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "services" / "core" / "src" / "accos"
DOMAIN_FORBIDDEN_IMPORTS = frozenset(
    {
        "boto3",
        "botocore",
        "celery",
        "fastapi",
        "httpx",
        "httpx2",
        "minio",
        "psycopg",
        "redis",
        "sqlalchemy",
        "starlette",
        "uvicorn",
    }
)
KERNEL_FORBIDDEN_IMPORTS = DOMAIN_FORBIDDEN_IMPORTS
MODULE_OWNER_INDEX = 2
PUBLIC_NAMESPACE_INDEX = 3
MIN_OWNED_MODULE_PARTS = PUBLIC_NAMESPACE_INDEX
MIN_PUBLIC_IMPORT_PARTS = PUBLIC_NAMESPACE_INDEX + 1


def module_name(path: Path) -> str:
    relative = path.relative_to(PACKAGE_ROOT.parent).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def imported_modules(path: Path, tree: ast.AST) -> Iterable[str]:
    current = module_name(path).split(".")
    package = current if path.name == "__init__.py" else current[:-1]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                if node.module:
                    yield node.module
                continue

            trim_count = node.level - 1
            base = package[: len(package) - trim_count] if trim_count else package
            suffix = node.module.split(".") if node.module else []
            resolved = ".".join([*base, *suffix])
            if resolved:
                yield resolved


def find_cycle(graph: dict[str, set[str]]) -> list[str] | None:
    visited: set[str] = set()
    active: list[str] = []
    active_set: set[str] = set()

    def visit(module: str) -> list[str] | None:
        visited.add(module)
        active.append(module)
        active_set.add(module)
        for dependency in sorted(graph[module]):
            if dependency not in graph:
                continue
            if dependency in active_set:
                start = active.index(dependency)
                return [*active[start:], dependency]
            if dependency not in visited:
                cycle = visit(dependency)
                if cycle:
                    return cycle
        active.pop()
        active_set.remove(module)
        return None

    for module in sorted(graph):
        if module not in visited:
            cycle = visit(module)
            if cycle:
                return cycle
    return None


def boundary_violations(source: str, dependency: str) -> Iterable[str]:
    source_parts = source.split(".")
    dependency_root = dependency.split(".", maxsplit=1)[0]
    dependency_parts = dependency.split(".")

    if source.startswith("accos.entrypoints") and dependency.startswith("accos.adapters"):
        yield "entrypoints must use composition and public ports, not private adapters"

    if len(source_parts) >= 4 and source_parts[:2] == ["accos", "adapters"]:
        owner = source_parts[2]
        if (
            len(dependency_parts) >= 3
            and dependency_parts[:2] == ["accos", "adapters"]
            and dependency_parts[2] not in {owner, "persistence"}
        ):
            yield "adapters must not import another owner's private adapter or tables"
        if (
            len(dependency_parts) >= 3
            and dependency_parts[:2] == ["accos", "modules"]
            and dependency_parts[2] != owner
            and (len(dependency_parts) < 4 or dependency_parts[3] != "public")
        ):
            yield "adapter cross-module imports must use the owner's public namespace"

    if source.startswith("accos.kernel") and dependency.startswith(
        ("accos.modules", "accos.adapters", "accos.entrypoints")
    ):
        yield "kernel must not import modules, adapters, or entrypoints"

    if source.startswith(("accos.kernel", "accos.modules")) and dependency.startswith(
        "accos.extensions"
    ):
        yield "core contracts must not import concrete extension packages"

    if source.startswith("accos.extensions") and dependency.startswith(
        ("accos.adapters", "accos.composition", "accos.entrypoints", "accos.modules")
    ):
        yield "extension contracts must not import core private repositories"

    if source.startswith("accos.kernel") and dependency_root in KERNEL_FORBIDDEN_IMPORTS:
        yield "kernel must not import framework or infrastructure SDKs"

    if "domain" in source_parts and (
        dependency_root in DOMAIN_FORBIDDEN_IMPORTS or dependency.startswith("accos.adapters")
    ):
        yield "domain code must not import frameworks or adapters"

    if "application" in source_parts and dependency.startswith("accos.adapters"):
        yield "application code must not import adapters"

    if len(source_parts) >= MIN_OWNED_MODULE_PARTS and source_parts[:MODULE_OWNER_INDEX] == [
        "accos",
        "modules",
    ]:
        source_owner = source_parts[MODULE_OWNER_INDEX]
        dependency_parts = dependency.split(".")
        if (
            len(dependency_parts) >= MIN_OWNED_MODULE_PARTS
            and dependency_parts[:MODULE_OWNER_INDEX] == ["accos", "modules"]
            and dependency_parts[MODULE_OWNER_INDEX] != source_owner
            and (
                len(dependency_parts) < MIN_PUBLIC_IMPORT_PARTS
                or dependency_parts[PUBLIC_NAMESPACE_INDEX] != "public"
            )
        ):
            yield "cross-module imports must target the owning module's public namespace"


def main() -> int:
    graph: dict[str, set[str]] = defaultdict(set)
    violations: list[str] = []

    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        source = module_name(path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for dependency in imported_modules(path, tree):
            if dependency.startswith("accos"):
                graph[source].add(dependency)
            for message in boundary_violations(source, dependency):
                relative = path.relative_to(REPOSITORY_ROOT).as_posix()
                violations.append(f"{relative}: {source} -> {dependency}: {message}")

    cycle = find_cycle(graph)
    if cycle:
        violations.append(f"Python dependency cycle: {' -> '.join(cycle)}")

    if violations:
        sys.stderr.write("\n".join(violations) + "\n")
        return 1

    sys.stdout.write("Python import boundaries: PASS\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
