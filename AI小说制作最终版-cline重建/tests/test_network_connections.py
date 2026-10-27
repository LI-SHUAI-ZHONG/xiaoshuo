# -*- coding: utf-8 -*-
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import generate_network_connections as generator


class NetworkConnectionTests(unittest.TestCase):
    def test_static_block_parse_and_dedup_priority(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "静态网络.txt"
            path.write_text(
                '{"source_index":{"A":{"targets":[{"target":"B","type":"触发","condition":"x","priority":3}]}}}\n'
                '{"source_index":{"A":{"targets":[{"target":"B","type":"触发","condition":"x","priority":1},{"target":"C","type":"嵌套","condition":"y","priority":2}]}}}',
                encoding="utf-8",
            )
            records, blocks = generator.parse_static(path)
            self.assertEqual(blocks, 2)
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["priority"], 1)

    def test_priority_sort(self):
        records = [{"source": "A", "target": "Z", "type": "x", "priority": 2}, {"source": "A", "target": "B", "type": "x", "priority": 1}]
        self.assertEqual(sorted(records, key=lambda x: (x["source"], x["priority"], x["target"], x["type"]))[0]["target"], "B")

    def test_dynamic_id_sequence_and_index_shape(self):
        ids = [f"C{i:05d}" for i in range(1, 4)]
        self.assertEqual(ids, ["C00001", "C00002", "C00003"])

    def test_difference(self):
        static = {("A", "B", "x"), ("A", "C", "y")}
        dynamic = {("A", "B", "x")}
        self.assertEqual(static - dynamic, {("A", "C", "y")})
        self.assertEqual(dynamic - static, set())

    def test_alias_granularity_is_not_merged(self):
        aliases = generator.build_aliases({"8.1_身体状态", "8.1_身体状态_饥饿"})
        self.assertEqual(aliases["exact_alias"], {})
        self.assertEqual(len(aliases["unresolved_similar"]), 1)


if __name__ == "__main__":
    unittest.main()