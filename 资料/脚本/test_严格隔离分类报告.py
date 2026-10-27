from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from 严格隔离分类报告 import _category


class StrictQuarantineClassificationTests(unittest.TestCase):
    def test_candidate_with_missing_identity_is_not_downgraded(self) -> None:
        category, _, _ = _category(["来源对象状态为 candidate", "类型连接对象缺少可核验标识"])
        self.assertEqual("candidate_identity_missing", category)

    def test_pending_requires_confirmation(self) -> None:
        category, _, _ = _category(["来源对象状态为 pending"])
        self.assertEqual("pending_requires_project_confirmation", category)

    def test_invalid_locator_is_recoverable_only_with_proof(self) -> None:
        category, _, _ = _category(["source_ref 文本数组或下标无效"])
        self.assertEqual("locator_invalid_or_out_of_range", category)


if __name__ == "__main__":
    unittest.main()