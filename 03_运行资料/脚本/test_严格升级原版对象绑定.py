from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("严格升级原版对象绑定.py")
SPEC = importlib.util.spec_from_file_location("strict_binding", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class StrictUpgradeBindingTests(unittest.TestCase):
    def test_binds_unique_identity_and_quarantines_ambiguous_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            index = root / MODULE.INDEX_PATH
            index.parent.mkdir(parents=True)
            index.write_text("\n".join(json.dumps(row) for row in [
                {"object_kind": "json_object", "identity": "C1", "object_id": "O1", "content_sha256": "h1", "source_file": "原始资料/动态网络.txt"},
                {"object_kind": "json_object", "identity": "C2", "object_id": "O2", "content_sha256": "h2", "source_file": "原始资料/动态网络.txt"},
                {"object_kind": "json_object", "identity": "C2", "object_id": "O3", "content_sha256": "h3", "source_file": "原始资料/动态网络.txt"},
            ]) + "\n", encoding="utf-8")
            batches = root / MODULE.FREEZE_ROOT / "严格升级批次"
            batches.mkdir(parents=True)
            batches.joinpath("SOURCE-UPGRADE-00001.json").write_text(json.dumps({"records": [{"upgrade_id": "U1", "binding_id": "B1", "source_id": "C1"}, {"upgrade_id": "U2", "binding_id": "B2", "source_id": "C2"}, {"upgrade_id": "U3", "binding_id": "B3", "source_id": "C3"}]}), encoding="utf-8")
            report = MODULE.bind(root)
            self.assertEqual({"conflict": 1, "unmatched": 1, "verified": 1}, report["binding_status_counts"])
            verified = (root / "文档" / "证据" / "严格升级原版对象绑定" / "bindings.jsonl").read_text(encoding="utf-8")
            self.assertIn('"original_object_id": "O1"', verified)


if __name__ == "__main__":
    unittest.main()