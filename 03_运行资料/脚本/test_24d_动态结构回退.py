from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS))
PIPELINE = SCRIPTS / "执行管道.py"
SPEC = importlib.util.spec_from_file_location("pipeline_24d", PIPELINE)
assert SPEC and SPEC.loader
PIPELINE_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PIPELINE_MODULE)

from 资料消费审计 import audit_network_consumption_contract


class DynamicFallbackContractTests(unittest.TestCase):
    def test_valid_dynamic_connections_do_not_report_fallback(self) -> None:
        connections, resolution = PIPELINE_MODULE._resolve_dynamic_connections({"connections": [{"id": "D1"}]})
        self.assertEqual([{"id": "D1"}], connections)
        self.assertFalse(resolution["fallback_used"])

    def test_static_shaped_dynamic_payload_is_rejected_as_dynamic_chain(self) -> None:
        with self.assertRaisesRegex(ValueError, "动态网络缺少 connections"):
            PIPELINE_MODULE._resolve_dynamic_connections({"source_index": {"A": {"targets": [{"target": "B"}]}}})

    def test_dynamic_top_level_list_rejects_non_object_entries(self) -> None:
        with self.assertRaisesRegex(ValueError, "每个连接项必须是对象"):
            PIPELINE_MODULE._resolve_dynamic_connections([{"id": "D1"}, "invalid"])

    def test_dynamic_connections_type_conflict_is_not_hidden_by_legacy_container(self) -> None:
        with self.assertRaisesRegex(ValueError, "connections 必须是列表"):
            PIPELINE_MODULE._resolve_dynamic_connections({
                "connections": "invalid",
                "动态网络连接_完整版": {"连接列表": [{"id": "D1"}]},
            })

    def test_static_connections_rejects_non_object_entries(self) -> None:
        with self.assertRaisesRegex(ValueError, "每个连接项必须是对象"):
            PIPELINE_MODULE._static_connections({"connections": [{"source": "A"}, None]})

    def test_static_source_index_rejects_non_object_targets(self) -> None:
        with self.assertRaisesRegex(ValueError, "每个连接项必须是对象"):
            PIPELINE_MODULE._static_connections({"source_index": {"A": {"targets": ["invalid"]}}})

    def test_network_audit_blocks_explicit_fallback_record(self) -> None:
        report = audit_network_consumption_contract("dynamic_chain", [{
            "chain_id": "D1", "status": "consumed", "fallback_used": True,
            "fallback_reason": "动态网络缺少 connections", "original_required_kind": "dynamic_chain",
        }])
        self.assertFalse(report["passed"])
        self.assertIn("跨源替代默认禁止", report["violations"][0]["reason"])


if __name__ == "__main__":
    unittest.main()