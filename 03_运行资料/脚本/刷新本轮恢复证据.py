"""Refresh derived replay evidence after targeted repair in the isolated copy."""
from __future__ import annotations

import json
from pathlib import Path

import 执行管道 as pipeline


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    pipeline.set_project_root(ROOT)
    config = pipeline.read_json(pipeline.PROJECT_CONFIG)
    registry = pipeline.build_registry(ROOT)
    matrix = pipeline._build_book_activation_matrix(config, pipeline.read_json(pipeline.CREATION_BINDINGS))[0]
    startup = pipeline._write_startup_binding_contract(config, registry)
    result = {
        "status": "passed",
        "project_root": str(ROOT),
        "project_id": config.get("project_id"),
        "matrix": {
            "material_count": matrix["material_count"],
            "assigned": matrix["coverage"]["assigned"],
            "deferred": matrix["coverage"]["deferred"],
        },
        "startup_contract": {
            "status": startup["status"],
            "path": "文档/证据/启动绑定合同.json",
        },
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()