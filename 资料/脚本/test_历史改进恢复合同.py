from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
import 执行管道 as pipeline
from 项目来源确认 import validate_confirmation


class HistoricalImprovementRecoveryContractTests(unittest.TestCase):
    def test_startup_contract_requires_and_records_each_six_source_registration(self) -> None:
        original_root = pipeline.PROJECT_ROOT
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            try:
                pipeline.set_project_root(root)
                resources = {
                    key: {"status": "parseable", "relative_path": f"原始资料/{key}.txt"}
                    for key in ("library", "type_system", "type_connections", "static_network", "dynamic_network", "anchor_network")
                }
                contract = pipeline._write_startup_binding_contract({"project_id": "p1"}, {"status": "passed", "resources": resources})
                self.assertEqual("passed", contract["status"])
                self.assertEqual(["资料库", "类型系统", "类型连接", "静态网络", "动态网络", "锚点网络"], contract["registered_source_kinds"])
                self.assertTrue(all(item["registered"] for item in contract["source_registration"].values()))

                del resources["anchor_network"]
                blocked = pipeline._write_startup_binding_contract({"project_id": "p1"}, {"status": "passed", "resources": resources})
                self.assertEqual("blocked", blocked["status"])
                self.assertIn("锚点网络", "；".join(blocked["blocking_reasons"]))
            finally:
                pipeline.set_project_root(original_root)

    def test_system_runtime_confirmation_allows_runtime_but_never_formal_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "配置" / "project_config.json"
            config.parent.mkdir(parents=True)
            config.write_text(json.dumps({"project_id": "p1"}, ensure_ascii=False), encoding="utf-8")
            confirmation = root / "配置" / "project_source_confirmation.json"
            confirmation.write_text(json.dumps({
                "schema_version": "project-source-confirmation-1.1",
                "project_id": "p1",
                "status": "system_runtime_confirmed",
                "source_quality_ack": True,
                "approval_actor": "system",
                "formal_fact_approval": False,
            }, ensure_ascii=False), encoding="utf-8")
            report = validate_confirmation(root)
            self.assertEqual("system_runtime_confirmed", report["status"])
            self.assertTrue(report["allow_runtime_pipeline"])
            self.assertFalse(report["allow_formal_pipeline"])
            self.assertEqual("draft_only", report["delivery_status"])
            self.assertEqual(str(confirmation.resolve()), report["confirmation_path"])
            persisted = json.loads((root / "文档" / "证据" / "项目来源确认报告.json").read_text(encoding="utf-8"))
            self.assertEqual(str(confirmation.resolve()), persisted["confirmation_path"])


if __name__ == "__main__":
    unittest.main()