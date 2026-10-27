from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from 三章金样本闸门 import CHAPTER_BLUEPRINTS, _evidence, build_micro_batch_queue, validate_artifacts


def _manifest(chapter: dict) -> dict:
    return {
        "chapter_id": chapter["chapter_id"],
        "chapter_decision": {key: chapter[key] for key in ("chapter_goal", "obstacle", "choice", "consequence", "state_change", "next_action_interface", "previous_action_interface") if key in chapter},
        "selected_evidence": _evidence({"动态网络.txt": "draft_usable", "静态网络.txt": "draft_usable", "锚点网络.txt": "draft_usable"}),
        "scenes": [{"scene_id": scene[0], "goal": scene[2], "obstacle": scene[3], "new_information": scene[4], "choice": scene[5], "consequence": scene[6]} for scene in chapter["scenes"]],
    }


class GoldenThreeChapterGateTests(unittest.TestCase):
    def test_accepts_complete_source_bounded_three_chapter_plan(self) -> None:
        report = validate_artifacts([_manifest(chapter) for chapter in CHAPTER_BLUEPRINTS])
        self.assertEqual("planning_gate_passed", report["status"])

    def test_rejects_candidate_source(self) -> None:
        manifests = [_manifest(chapter) for chapter in CHAPTER_BLUEPRINTS]
        manifests[0]["selected_evidence"][0]["evidence_level"] = "candidate"
        self.assertEqual("blocked", validate_artifacts(manifests)["status"])

    def test_rejects_missing_scene_consequence(self) -> None:
        manifests = [_manifest(chapter) for chapter in CHAPTER_BLUEPRINTS]
        manifests[1]["scenes"][0]["consequence"] = ""
        self.assertEqual("blocked", validate_artifacts(manifests)["status"])

    def test_micro_batches_are_six_or_less_and_cannot_write_prose(self) -> None:
        plan = {"records": [{"consumption_id": f"PC-{number:05d}", "source_kind": "动态网络"} for number in range(1, 14)]}
        batches = build_micro_batch_queue(plan, {"动态网络.txt": "draft_usable"})
        self.assertEqual(3, len(batches))
        self.assertTrue(all(len(batch["records"]) <= 6 and batch["prose_write_allowed"] is False for batch in batches))

    def test_rejects_broken_cross_chapter_action_interface(self) -> None:
        manifests = [_manifest(chapter) for chapter in CHAPTER_BLUEPRINTS]
        manifests[2]["chapter_decision"]["previous_action_interface"] = "不连续"
        self.assertEqual("blocked", validate_artifacts(manifests)["status"])


if __name__ == "__main__":
    unittest.main()