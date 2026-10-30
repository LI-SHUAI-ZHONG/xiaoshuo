"""Static regression checks for source-production capability reporting."""
from __future__ import annotations

import ast
import unittest
from pathlib import Path


PIPELINE = Path(__file__).with_name("执行管道.py")


class SourceCapabilityGateStaticTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tree = ast.parse(PIPELINE.read_text(encoding="utf-8-sig"))
        self.main = next(
            node for node in self.tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "main"
        )

    def test_failed_capability_is_reported_without_startup_runtime_error(self) -> None:
        audit_index = next(
            index for index, node in enumerate(self.main.body)
            if isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "audit_source_production"
        )
        self.assertEqual(ast.unparse(self.main.body[audit_index].value.args[0]), "PROJECT_ROOT")
        assignment = self.main.body[audit_index + 1]
        self.assertIsInstance(assignment, ast.Assign)
        self.assertEqual(ast.unparse(assignment.targets[0]), "source_capability_blocked")
        self.assertEqual(ast.unparse(assignment.value), "source_capability['status'] != 'passed'")
        self.assertFalse(
            any(isinstance(node, ast.Raise) for node in self.main.body[audit_index + 1:audit_index + 2]),
            "audit_source_production 返回 failed 时，main 初始化不得在此处抛 RuntimeError",
        )

        dict_nodes = [node for node in ast.walk(self.main) if isinstance(node, ast.Dict)]
        context = next(
            node for node in dict_nodes
            if "source_production_capability_blocked" in {
                key.value for key in node.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
            and "delivery_status" in {
                key.value for key in node.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
            and ast.unparse(next(
                value for key, value in zip(node.keys, node.values)
                if isinstance(key, ast.Constant) and key.value == "source_production_capability"
            )) == "source_capability"
        )
        values = {
            key.value: value for key, value in zip(context.keys, context.values)
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }
        self.assertIn("source_production_capability", values)
        self.assertIsInstance(values["source_production_capability_blocked"], ast.Name)
        self.assertEqual(values["source_production_capability_blocked"].id, "source_capability_blocked")
        self.assertIn("draft_only", ast.unparse(values["delivery_status"]))
        self.assertIn("source_capability_blocked", ast.unparse(values["delivery_status"]))

        header = next(
            node for node in dict_nodes
            if "record_type" in {
                key.value for key in node.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
        )
        header_values = {
            key.value: value for key, value in zip(header.keys, header.values)
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }
        self.assertEqual(
            ast.unparse(header_values["source_production_capability_status"]),
            "source_capability['status']",
        )
        self.assertEqual(ast.unparse(header_values["source_production_capability_blocked"]), "source_capability_blocked")

    def test_runtime_admission_refresh_uses_creation_contract(self) -> None:
        calls = [
            node for node in ast.walk(self.main)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "validate_execution_contract"
        ]
        phases = [
            next((keyword.value.value for keyword in call.keywords if keyword.arg == "phase" and isinstance(keyword.value, ast.Constant)), None)
            for call in calls
        ]
        self.assertIn("creation", phases)

    def test_empty_runtime_package_blocks_module09_after_module08(self) -> None:
        source = ast.unparse(self.main)
        self.assertIn("if module_id == '08' and record['status'] == 'success'", source)
        self.assertIn("if not package_check['passed']:", source)
        self.assertIn('blocked = True', source)
        self.assertIn("if blocked and module_id not in {'11'}", source)

        execute_11 = next(
            node for node in self.tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "execute_11"
        )
        execute_11_source = ast.unparse(execute_11)
        self.assertIn("not source_capability_blocked", execute_11_source)
        self.assertIn("'draft_only'", execute_11_source)


if __name__ == "__main__":
    unittest.main()