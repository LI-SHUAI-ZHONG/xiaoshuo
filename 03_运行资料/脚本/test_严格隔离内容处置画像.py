from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from 严格隔离内容处置画像 import _profile, _strategy


class StrictQuarantineContentDispositionProfileTests(unittest.TestCase):
    def test_template_candidate_requires_template_provenance_review(self) -> None:
        key = _profile({}, {"status": "candidate", "evidence_type": "template", "generation_method": "template", "primary_type_id": "GENRE_A"})
        self.assertEqual("template_provenance_and_scope_review", _strategy(key)[0])

    def test_unresolved_content_requires_independent_replacement(self) -> None:
        key = _profile({}, None)
        self.assertEqual("independent_replacement_source", _strategy(key)[0])


if __name__ == "__main__":
    unittest.main()