from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PATH = Path(__file__).with_name("文本生成模型.py")
SPEC = importlib.util.spec_from_file_location("text_generation_model_test", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TextGenerationModelTests(unittest.TestCase):
    def test_ollama_maps_output_token_budget_to_num_predict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "配置"; config.mkdir()
            (config / "文本生成模型.json").write_text(json.dumps({"provider": "ollama", "ollama": {"base_url": "http://model", "model": "test", "timeout_seconds": 1, "temperature": 0.1, "max_output_tokens": 1024}}), encoding="utf-8")
            with patch.object(MODULE, "_ollama_model", return_value="test"), patch.object(MODULE, "_request", return_value={"message": {"content": "{}"}}) as request:
                MODULE.generate_json(root, "system", "prompt")
            self.assertEqual(1024, request.call_args.args[1]["options"]["num_predict"])

    def test_omits_output_token_budget_when_not_configured(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "配置"; config.mkdir()
            (config / "文本生成模型.json").write_text(json.dumps({"provider": "ollama", "ollama": {"base_url": "http://model", "model": "test"}}), encoding="utf-8")
            with patch.object(MODULE, "_ollama_model", return_value="test"), patch.object(MODULE, "_request", return_value={"message": {"content": "{}"}}) as request:
                MODULE.generate_json(root, "system", "prompt")
            self.assertNotIn("num_predict", request.call_args.args[1]["options"])

    def test_plain_text_ollama_request_does_not_enforce_json_format(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "配置"; config.mkdir()
            (config / "文本生成模型.json").write_text(json.dumps({"provider": "ollama", "ollama": {"base_url": "http://model", "model": "test"}}), encoding="utf-8")
            with patch.object(MODULE, "_ollama_model", return_value="test"), patch.object(MODULE, "_request", return_value={"response": "一段正文。"}) as request:
                text, metadata = MODULE.generate_text(root, "system", "prompt")
            self.assertEqual("一段正文。", text)
            self.assertEqual("test", metadata["model"])
            self.assertNotIn("format", request.call_args.args[1])


if __name__ == "__main__":
    unittest.main()