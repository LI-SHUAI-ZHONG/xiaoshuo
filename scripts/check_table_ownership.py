"""Static ownership gate used by final acceptance, never by the construction entry.

This checks registered ORM declarations and literal SQL write targets. It does
not claim to prove arbitrary dynamic Python safe; dynamic SQL at these boundaries
is rejected and runtime permission/transaction tests remain mandatory.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WRITE_TARGET = re.compile(
    r"\b(?:insert\s+into|update|delete\s+from|merge\s+into|truncate\s+(?:table\s+)?)\s*"
    r'(?:"?accos"?\.)?"?([a-z_][a-z_0-9]*)',
    re.IGNORECASE,
)
READ_ONLY_FORBIDDEN = frozenset(
    {
        "add",
        "add_all",
        "delete",
        "merge",
        "flush",
        "commit",
        "insert",
        "update",
        "bulk_save_objects",
        "bulk_insert_mappings",
    }
)


def inspect_sources(root: Path, registry: dict[str, Any]) -> list[str]:
    entries = registry["tables"]
    owners = {row["table"]: row for row in entries}
    errors: list[str] = []
    if len(owners) != len(entries):
        errors.append("Table registry contains more than one owner for the same table")
    observed: dict[str, str] = {}
    package_root = root / "services/core/src/accos"
    read_only = {row["module"] for row in registry.get("read_only_exceptions", [])}
    for file in sorted(package_root.rglob("*.py")):
        relative = file.relative_to(root).as_posix()
        parts = file.relative_to(package_root).parts
        source_owner = parts[1] if parts[0] == "adapters" and len(parts) >= 3 else None
        module = "accos." + ".".join(file.relative_to(package_root).with_suffix("").parts)
        for node in ast.walk(ast.parse(file.read_text(encoding="utf-8-sig"))):
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "__tablename__"
                for target in node.targets
            ):
                if not isinstance(node.value, ast.Constant) or not isinstance(
                    node.value.value, str
                ):
                    errors.append(f"{relative}: ORM table names must be literal registered names")
                    continue
                table = node.value.value
                if table in observed:
                    errors.append(f"{relative}: duplicate table declaration {table}")
                observed[table] = relative
                registered = owners.get(table)
                if registered is None:
                    errors.append(f"{relative}: unregistered table {table}")
                elif registered["declaration"] != relative or registered["owner"] != source_owner:
                    errors.append(f"{relative}: {table} belongs to {registered['owner']}")
            if not isinstance(node, ast.Call):
                continue
            name = (
                node.func.attr
                if isinstance(node.func, ast.Attribute)
                else (node.func.id if isinstance(node.func, ast.Name) else "")
            )
            if module in read_only and name in READ_ONLY_FORBIDDEN:
                errors.append(f"{relative}: a read-only projection cannot call {name}")
            if name not in {"text", "exec_driver_sql"} or not node.args:
                continue
            sql = node.args[0]
            if not isinstance(sql, ast.Constant) or not isinstance(sql.value, str):
                errors.append(f"{relative}: dynamic SQL requires a reviewed owner-specific adapter")
                continue
            for match in WRITE_TARGET.finditer(sql.value):
                table = match.group(1).lower()
                registered = owners.get(table)
                if module in read_only or registered is None or registered["owner"] != source_owner:
                    errors.append(f"{relative}: forbidden SQL write to {table}")
    errors.extend(
        f"Registered table has no declaration: {table}"
        for table in sorted(owners.keys() - observed.keys())
    )
    return errors


def main() -> int:
    registry = json.loads((ROOT / "docs/contracts/ownership.json").read_text(encoding="utf-8"))
    errors = inspect_sources(ROOT, registry)
    if errors:
        sys.stderr.write("\n".join(errors) + "\n")
        return 1
    print("ORM ownership and SQL write boundaries: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
