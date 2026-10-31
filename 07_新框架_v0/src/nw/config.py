"""TOML settings. Secrets are resolved from the environment only."""
from dataclasses import dataclass
import math
import os
from pathlib import Path
import tomllib
from urllib.parse import urlsplit

from nw.llm.base import LLMProvider
from nw.llm.ollama import OllamaProvider
from nw.llm.openai_compat import OpenAICompatProvider

ROOT = Path(__file__).resolve().parents[2]


class ConfigRequired(ValueError):
    pass


@dataclass
class Config:
    provider: str
    base_url: str
    model: str
    api_key_env: str
    timeout: float
    params: dict
    workspace: Path


def load_config(path: Path) -> Config:
    try:
        data = tomllib.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise ConfigRequired('Provide a readable valid TOML file with --config') from None
    try:
        cfg = data['model']
        if set(cfg) - {'provider', 'base_url', 'model', 'api_key_env', 'timeout'}:
            raise ValueError()
        provider, url, model = cfg['provider'], cfg['base_url'], cfg['model']
        if provider not in ('ollama', 'openai_compat') or not isinstance(model, str) or not model.strip() or model == 'REPLACE_WITH_MODEL_NAME':
            raise ValueError()
        parts = urlsplit(url)
        if parts.scheme not in ('http', 'https') or not parts.hostname or parts.hostname.endswith('.invalid') or parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError()
        key_env = cfg.get('api_key_env', '')
        if not isinstance(key_env, str) or (provider == 'openai_compat' and not key_env):
            raise ValueError()
        timeout = float(cfg.get('timeout', 120))
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError()
        params = data.get('params', {})
        allowed = ({'temperature', 'top_p', 'max_tokens', 'max_completion_tokens', 'seed', 'stop'}
                   if provider == 'openai_compat' else {'temperature', 'top_p', 'top_k', 'num_predict', 'seed', 'stop', 'repeat_penalty'})
        if not isinstance(params, dict) or set(params) - allowed:
            raise ValueError()
        workspace = Path(data.get('paths', {}).get('workspace', str(ROOT / 'workspace')))
        if not workspace.is_absolute():
            workspace = path.resolve().parent / workspace
        return Config(provider, url.rstrip('/'), model, key_env, timeout, params, workspace)
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ConfigRequired('Set valid model.provider, base_url, model, api_key_env (compatible API), timeout and supported params; never put keys in TOML') from None


def make_provider(config: Config, selected: str | None = None) -> LLMProvider:
    if selected and selected != config.provider:
        raise ConfigRequired('--provider must match model.provider in the configuration')
    if config.provider == 'ollama':
        return OllamaProvider(config.base_url, config.timeout)
    key = os.environ.get(config.api_key_env, '')
    if not key:
        raise ConfigRequired(f'Missing environment variable: {config.api_key_env}')
    return OpenAICompatProvider(config.base_url, key, config.timeout)
