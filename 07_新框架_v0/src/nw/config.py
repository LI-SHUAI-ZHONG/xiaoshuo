"""TOML settings. Secrets are resolved from the environment only."""
from dataclasses import dataclass, field, replace
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
    source_driven: bool = True
    stage_models: dict[str, dict] = field(default_factory=dict)


def _validate_endpoint(provider: str, url: str, model: str, key_env: str, timeout: float, params: dict) -> dict:
    if provider not in ('ollama', 'openai_compat') or not isinstance(model, str) or not model.strip() or model == 'REPLACE_WITH_MODEL_NAME':
        raise ValueError()
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname or parts.hostname.endswith('.invalid') or parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError()
    if not isinstance(key_env, str) or (provider == 'openai_compat' and not key_env):
        raise ValueError()
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError()
    allowed = ({'temperature', 'top_p', 'max_tokens', 'max_completion_tokens', 'seed', 'stop'}
               if provider == 'openai_compat' else {'temperature', 'top_p', 'top_k', 'num_predict', 'seed', 'stop', 'repeat_penalty'})
    if not isinstance(params, dict) or set(params) - allowed:
        raise ValueError()
    return {'provider': provider, 'base_url': url.rstrip('/'), 'model': model.strip(),
            'api_key_env': key_env, 'timeout': timeout, 'params': dict(params)}


def load_config(path: Path) -> Config:
    try:
        data = tomllib.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise ConfigRequired('Provide a readable valid TOML file with --config') from None
    try:
        cfg = data['model']
        if set(cfg) - {'provider', 'base_url', 'model', 'api_key_env', 'timeout'}:
            raise ValueError()
        base = _validate_endpoint(
            cfg['provider'], cfg['base_url'], cfg['model'],
            cfg.get('api_key_env', ''), float(cfg.get('timeout', 120)),
            data.get('params', {}),
        )
        workspace = Path(data.get('paths', {}).get('workspace', str(ROOT / 'workspace')))
        if not workspace.is_absolute():
            workspace = path.resolve().parent / workspace
        workflow=data.get('workflow',{})
        if not isinstance(workflow,dict) or set(workflow)-{'source_driven'} or type(workflow.get('source_driven',True)) is not bool:
            raise ValueError()
        raw_stages = data.get('stage_models', {})
        if not isinstance(raw_stages, dict):
            raise ValueError()
        stage_models: dict[str, dict] = {}
        for stage_name, spec in raw_stages.items():
            if not isinstance(stage_name, str) or not stage_name.strip():
                raise ValueError()
            if isinstance(spec, str):
                stage_models[stage_name] = _validate_endpoint(
                    base['provider'], base['base_url'], spec, base['api_key_env'], base['timeout'], base['params'],
                )
            elif isinstance(spec, dict):
                if set(spec) - {'provider', 'base_url', 'model', 'api_key_env', 'timeout', 'params'}:
                    raise ValueError()
                sp_prov = spec.get('provider', base['provider'])
                sp_params = spec.get('params', base['params'] if sp_prov == base['provider'] else {})
                stage_models[stage_name] = _validate_endpoint(
                    sp_prov,
                    spec.get('base_url', base['base_url']),
                    spec['model'],
                    spec.get('api_key_env', base['api_key_env'] if sp_prov == base['provider'] else ''),
                    float(spec.get('timeout', base['timeout'])),
                    sp_params,
                )
            else:
                raise ValueError()
        return Config(base['provider'], base['base_url'], base['model'], base['api_key_env'],
                      base['timeout'], base['params'], workspace, workflow.get('source_driven', True), stage_models)
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ConfigRequired('Set valid model.provider, base_url, model, api_key_env (compatible API), timeout and supported params; never put keys in TOML') from None


def resolve_stage_runtime(config: Config, default_provider: LLMProvider, stage: str) -> tuple[Config, LLMProvider]:
    """Return stage-specific (Config, LLMProvider) when configured, else (config, default_provider)."""
    spec = config.stage_models.get(stage)
    if not spec or default_provider.name == 'fake':
        return config, default_provider
    stage_cfg = replace(
        config,
        provider=spec['provider'],
        base_url=spec['base_url'],
        model=spec['model'],
        api_key_env=spec['api_key_env'],
        timeout=spec['timeout'],
        params=dict(spec['params']),
    )
    if (stage_cfg.provider == config.provider and stage_cfg.base_url == config.base_url
            and stage_cfg.api_key_env == config.api_key_env and stage_cfg.timeout == config.timeout):
        return stage_cfg, default_provider
    return stage_cfg, make_provider(stage_cfg)


def make_provider(config: Config, selected: str | None = None) -> LLMProvider:
    if selected and selected != config.provider:
        raise ConfigRequired('--provider must match model.provider in the configuration')
    if config.provider == 'ollama':
        return OllamaProvider(config.base_url, config.timeout)
    key = os.environ.get(config.api_key_env, '')
    if not key:
        raise ConfigRequired(f'Missing environment variable: {config.api_key_env}')
    return OpenAICompatProvider(config.base_url, key, config.timeout)
