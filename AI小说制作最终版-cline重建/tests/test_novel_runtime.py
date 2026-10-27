# -*- coding: utf-8 -*-
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "工具" / "小说生产运行时.py"


class NovelRuntimeE2ETest(unittest.TestCase):
    def run_command(self, command, project, *extra):
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, str(RUNTIME), command, "--root", str(ROOT), "--project", str(project),
             "--project-id", "test-runtime", "--project-name", "测试闭环", "--type", "悬疑",
             "--genre", "悬疑", "--request", "小说：验证网络资料到章节正文的闭环", *extra],
            capture_output=True, text=True, encoding="utf-8", errors="replace", env=environment, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_full_pipeline_and_resume(self):
        with tempfile.TemporaryDirectory(prefix="novel-runtime-") as directory:
            project = Path(directory) / "测试闭环"
            result = self.run_command("run", project)
            self.assertEqual(result["status"], "AUTO_CONTINUE")
            self.assertTrue(list((project / "正文" / "卷01").glob("第001章_*.md")))
            self.assertTrue((project / "规划" / "资料驱动设计" / "golden_three_tasks.json").exists())
            audit = json.loads((project / "检查报告" / "资料调用审计.json").read_text(encoding="utf-8"))
            self.assertGreater(audit["selected_network_evidence"]["selected_count"], 0)
            self.assertIn("not_used_reasons", audit["selected_network_evidence"])
            synthesis = audit["synthesis_decisions"]["decisions"]
            self.assertTrue(all(synthesis[module]["status"] == "applied" for module in ("MOD-STATIC", "MOD-DYNAMIC", "MOD-ANCHOR", "MOD-CONNECTION")))
            text = next((project / "正文" / "卷01").glob("第001章_*.md")).read_text(encoding="utf-8")
            self.assertTrue(all(term in text for term in ("静态网络", "动态网络", "锚点网络")))
            self.run_command("plan", project, "--chapter", "2")
            self.run_command("generate", project, "--chapter", "2")
            check = self.run_command("check", project)
            self.assertEqual(check["status"], "PASS")
            self.assertEqual(check["next_chapter"], 3)

    def test_existing_formal_text_is_never_overwritten(self):
        with tempfile.TemporaryDirectory(prefix="novel-runtime-") as directory:
            project = Path(directory) / "测试拒绝覆盖"
            self.run_command("run", project)
            result = subprocess.run(
                [sys.executable, str(RUNTIME), "generate", "--root", str(ROOT), "--project", str(project), "--chapter", "1"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8"}, check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("正式正文已存在", result.stdout)


if __name__ == "__main__":
    unittest.main()