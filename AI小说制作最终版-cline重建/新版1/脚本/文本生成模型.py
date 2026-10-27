"""Small dependency-free clients for local Ollama and OpenAI-compatible chat APIs."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


class TextGenerationError(RuntimeError):
    pass


def load_settings(project_root: str | Path) -> dict[str, Any]:
    path = Path(project_root) / "配置" / "文本生成模型.json"
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TextGenerationError(f"无法读取模型配置：{path}") from exc


def _request(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        detail = "请求超时" if isinstance(exc, TimeoutError) else str(exc)
        raise TextGenerationError(f"模型请求失败：url={url}；timeout_seconds={timeout}；detail={detail}") from exc


def _ollama_model(base_url: str, configured: str, timeout: int) -> str:
    try:
        with urllib.request.urlopen(f"{base_url.rstrip('/')}/api/tags", timeout=timeout) as response:
            models = json.loads(response.read().decode("utf-8")).get("models", [])
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise TextGenerationError("无法连接 Ollama；请启动服务并确认 http://127.0.0.1:11434 可访问。") from exc
    names = [str(item.get("name", "")) for item in models if "embedding" not in item.get("capabilities", [])]
    if configured.strip():
        if configured.strip() not in names:
            raise TextGenerationError(f"Ollama 模型 {configured.strip()} 不存在或不具备聊天生成能力。")
        return configured.strip()
    if not names:
        raise TextGenerationError("Ollama 未安装可聊天生成的模型；当前 embedding 模型不能写正文。请执行 ollama pull qwen2.5:7b，或配置 OpenAI 兼容接口。")
    return names[0]


def generate_json(project_root: str | Path, system: str, prompt: str, schema: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, str]]:
    settings = load_settings(project_root)
    provider = str(settings.get("provider", "ollama"))
    if provider == "ollama":
        config = settings.get("ollama", {})
        base_url = str(config.get("base_url", "http://127.0.0.1:11434")).rstrip("/")
        timeout = int(config.get("timeout_seconds", 180))
        model = _ollama_model(base_url, str(config.get("model", "")), timeout)
        options = {"temperature": config.get("temperature", 0.55)}
        if config.get("max_output_tokens") is not None:
            options["num_predict"] = int(config["max_output_tokens"])
        response = _request(f"{base_url}/api/generate", {"model": model, "stream": False, "format": schema or "json", "options": options, "prompt": f"系统要求：{system}\n用户任务：{prompt}"}, {"Content-Type": "application/json"}, timeout)
        content = response.get("response", "") or response.get("message", {}).get("content", "")
        metadata = {"provider": provider, "model": model, "structured_output": "json_schema" if schema else "json_object"}
    elif provider == "openai_compatible":
        config = settings.get("openai_compatible", {})
        base_url = os.environ.get(str(config.get("base_url_env", "OPENAI_BASE_URL")), "").rstrip("/")
        api_key = os.environ.get(str(config.get("api_key_env", "OPENAI_API_KEY")), "")
        model = os.environ.get(str(config.get("model_env", "OPENAI_MODEL")), "")
        if not base_url or not api_key or not model:
            raise TextGenerationError("OpenAI 兼容配置不完整；请设置 OPENAI_BASE_URL、OPENAI_API_KEY 和 OPENAI_MODEL 环境变量。")
        timeout = int(config.get("timeout_seconds", 180))
        payload = {"model": model, "temperature": config.get("temperature", 0.55), "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
        if config.get("max_output_tokens") is not None:
            payload["max_tokens"] = int(config["max_output_tokens"])
        response = _request(f"{base_url}/chat/completions", payload, {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}, timeout)
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        metadata = {"provider": provider, "model": model, "structured_output": "json_schema" if schema else "json_object"}
    else:
        raise TextGenerationError(f"不支持的模型提供方：{provider}")
    try:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()
        return json.loads(cleaned), metadata
    except json.JSONDecodeError as exc:
        raise TextGenerationError("模型未返回有效 JSON，未写入正文。") from exc


def generate_text(project_root: str | Path, system: str, prompt: str) -> tuple[str, dict[str, str]]:
    """Generate plain prose without spending the model output budget on JSON syntax."""
    settings = load_settings(project_root)
    provider = str(settings.get("provider", "ollama"))
    if provider == "ollama":
        config = settings.get("ollama", {})
        base_url = str(config.get("base_url", "http://127.0.0.1:11434")).rstrip("/")
        timeout = int(config.get("timeout_seconds", 180))
        model = _ollama_model(base_url, str(config.get("model", "")), timeout)
        options = {"temperature": config.get("temperature", 0.55)}
        if config.get("max_output_tokens") is not None:
            options["num_predict"] = int(config["max_output_tokens"])
        response = _request(f"{base_url}/api/generate", {"model": model, "stream": False, "options": options, "prompt": f"系统要求：{system}\n用户任务：{prompt}"}, {"Content-Type": "application/json"}, timeout)
        content = response.get("response", "") or response.get("message", {}).get("content", "")
        metadata = {"provider": provider, "model": model}
    elif provider == "openai_compatible":
        config = settings.get("openai_compatible", {})
        base_url = os.environ.get(str(config.get("base_url_env", "OPENAI_BASE_URL")), "").rstrip("/")
        api_key = os.environ.get(str(config.get("api_key_env", "OPENAI_API_KEY")), "")
        model = os.environ.get(str(config.get("model_env", "OPENAI_MODEL")), "")
        if not base_url or not api_key or not model:
            raise TextGenerationError("OpenAI 兼容配置不完整；请设置 OPENAI_BASE_URL、OPENAI_API_KEY 和 OPENAI_MODEL 环境变量。")
        timeout = int(config.get("timeout_seconds", 180))
        payload = {"model": model, "temperature": config.get("temperature", 0.55), "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
        if config.get("max_output_tokens") is not None:
            payload["max_tokens"] = int(config["max_output_tokens"])
        response = _request(f"{base_url}/chat/completions", payload, {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}, timeout)
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        metadata = {"provider": provider, "model": model}
    else:
        raise TextGenerationError(f"不支持的模型提供方：{provider}")
    cleaned = re.sub(r"^```(?:text)?\s*|\s*```$", "", str(content).strip(), flags=re.IGNORECASE | re.DOTALL).strip()
    if not cleaned:
        raise TextGenerationError("模型未返回正文，未写入正文。")
    return re.sub(r"\s+", "", cleaned), metadata