"""Generic API settings save configuration without generating text or fallback defaults."""
from pathlib import Path

import pytest

from nw.config import load_config
from nw.studio.api import StudioService


def api_payload() -> dict:
    return {'model': {'base_url': 'https://writing.example.test/v1', 'model': 'author-model',
                      'api_key_env': 'WRITING_TEST_API_KEY', 'timeout': 180},
            'params': {'temperature': 0.4}, 'stage_models': {'review': {'model': 'review-model'}},
            'source_driven': True}


def test_generic_api_default_saves_names_and_does_not_call_model(tmp_path: Path, monkeypatch) -> None:
    def unexpected_network(*args, **kwargs):
        raise AssertionError('Saving API settings must not call the model')
    monkeypatch.setattr('nw.llm.openai_compat.post', unexpected_network)
    monkeypatch.setenv('WRITING_TEST_API_KEY', 'isolated-test-secret-not-real')
    service=StudioService(tmp_path/'data', config_path=tmp_path/'config.toml')
    saved=service.save_routing_config(api_payload())
    cfg=load_config(service.config_path)
    assert saved['saved'] is True
    assert cfg.provider == 'openai_compat'
    assert cfg.base_url == 'https://writing.example.test/v1'
    assert cfg.model == 'author-model'
    assert cfg.stage_models['review']['model'] == 'review-model'
    assert cfg.stage_models['review']['provider'] == 'openai_compat'
    assert cfg.workspace == service.workspace
    assert cfg.source_driven is True
    assert saved['status']['env_present']['WRITING_TEST_API_KEY'] is True
    assert 'isolated-test-secret-not-real' not in saved['toml']


@pytest.mark.parametrize('field', ['base_url', 'model', 'api_key_env'])
def test_missing_api_fields_do_not_write_ollama_fallback_or_replace_saved_config(tmp_path: Path, field: str) -> None:
    service=StudioService(tmp_path/'data', config_path=tmp_path/'config.toml')
    service.save_routing_config(api_payload())
    before=service.config_path.read_text(encoding='utf-8')
    payload=api_payload()
    payload['model'][field]=''
    with pytest.raises(ValueError, match='请填写'):
        service.save_routing_config(payload)
    assert service.config_path.read_text(encoding='utf-8') == before
    assert '11434' not in before and 'qwen' not in before and 'ollama' not in before
