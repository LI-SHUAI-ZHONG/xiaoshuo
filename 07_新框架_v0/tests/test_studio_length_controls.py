"""Studio persists independent book-length choices and per-model working windows."""
import json

import pytest

from nw.config import ConfigRequired, load_config, resolve_stage_runtime
from nw.llm.openai_compat import OpenAICompatProvider
from nw.studio.api import StudioService
from nw.studio.production_inputs import freeze_wizard, governance
from nw.studio.production_length import retire_unstarted_book
from nw.studio.repository_git import shared_config_safe
from test_studio_v3_production import app, wizard


def test_model_windows_round_trip_and_inherit_without_expanding_saved_fields(tmp_path):
    api = StudioService(tmp_path / 'workspace', config_path=tmp_path / 'studio.config.toml')
    model = {'provider': 'openai_compat', 'model': 'author', 'base_url': 'https://writing.example.test/v1',
             'api_key_env': 'ISOLATED_KEY', 'context_window_tokens': 64000}
    stages = {'review': {'model': 'editor', 'context_window_tokens': 32000}, 'revise': {'context_window_tokens': 48000},
              'plan': 'planner'}
    api.save_routing_config({'model': model, 'stage_models': stages})
    loaded = load_config(api.config_path)
    endpoint = OpenAICompatProvider(loaded.base_url, 'test', loaded.timeout)
    assert 'context_window_tokens' not in loaded.params
    for name, expected_model, window in [('review', 'editor', 32000), ('revise', 'author', 48000),
                                         ('plan', 'planner', None), ('write', 'author', 64000)]:
        cfg, _ = resolve_stage_runtime(loaded, endpoint, name)
        assert (cfg.model, cfg.context_window_tokens) == (expected_model, window)
        assert 'context_window_tokens' not in cfg.params
    assert api.get_routing_config()['current']['stage_overrides']['revise'] == {'context_window_tokens': 48000}
    shared_config_safe(api.config_path)
    saved = api.config_path.read_bytes()
    for value in (True, -7, 1.5, 'secret'):
        with pytest.raises((ValueError, ConfigRequired)):
            api.save_routing_config({'model': {**model, 'context_window_tokens': value}})
        assert api.config_path.read_bytes() == saved
    # Empty model-specific settings continue to follow subsequent default model changes.
    api.save_routing_config({'model': {**model, 'model': 'new-author'}, 'stage_models': stages})
    reloaded = load_config(api.config_path)
    assert resolve_stage_runtime(reloaded, endpoint, 'revise')[0].model == 'new-author'


def test_wizard_lengths_persist_adjust_without_retconning_old_frozen_inputs(app):
    raw = {**wizard(app), 'auto_length': True, 'target_words': 160000, 'chapter_count': 40,
           'chapter_target_words': 4000, 'scene_target_words': 1200, 'word_tolerance_pct': 5,
           'budget': {'context_char_limit': 40000, 'output_limit': 2048}}
    book = app.create(raw)['novel']
    first = book['job_id']
    original = app.detail(book['id'])['length_plan']
    assert (original['target_words'],original['minimum_words'],original['accepted_words']) == (160000,152000,0)
    assert original['budget']['output_limit'] == 2048
    with app.open_store(book) as store:
        initial = store.connection.execute('SELECT request_json FROM novel_jobs WHERE id=?',(first,)).fetchone()[0]
        assert json.loads(initial)['governance_inputs']['plot_design']['length_auto']
        assert json.loads(initial)['governance_inputs']['plot_design']['length_policy']['chapter_target_words'] == 4000
    changed = app.configure_length(book['id'], {'target_words': 121, 'chapter_target_words': None,
        'word_tolerance_pct': 1, 'budget': {'output_limit': 4096}})['length_plan']
    assert changed['minimum_words'] == 120 and changed['remaining_words'] == 121
    assert changed['budget']['context_char_limit'] == 40000 and 'chapter_target_words' not in changed
    reopened = app.db.get(book['id'])
    assert governance(reopened['wizard'])['plot_design']['length_policy']['target_words'] == 121
    with app.open_store(book) as store:
        retire_unstarted_book(store, reopened, app.budget(reopened['wizard']['call_budget']))
        status, request = store.connection.execute('SELECT status,request_json FROM novel_jobs WHERE id=?',(first,)).fetchone()
        assert request == initial and status == 'CANCELLED'
        next_job = app._new_job(reopened, {}, store)
        frozen = json.loads(store.connection.execute('SELECT request_json FROM novel_jobs WHERE id=?',(next_job,)).fetchone()[0])
        assert frozen['governance_inputs']['plot_design']['length_policy']['target_words'] == 121
        assert frozen['budget']['output_limit'] == 4096 and frozen['budget']['context_char_limit'] == 40000
    assert len([e for e in app.timeline(book['id'])['events'] if e['kind'] == 'length']) == 1


@pytest.mark.parametrize('field,value',[('target_words',True),('scene_target_words',12.5),('word_tolerance_pct',100)])
def test_invalid_lengths_cannot_enter_project_or_wizard(app, field, value):
    with pytest.raises(ValueError, match='篇幅'):
        freeze_wizard({**wizard(app),field:value}, app.library)
    book = app.create(wizard(app))['novel']
    with pytest.raises(ValueError, match='篇幅'):
        app.configure_length(book['id'], {field:value})
    assert field not in app.db.get(book['id'])['wizard']


def test_revision_budget_is_validated_before_creating_a_novel(app):
    assert app.budget({'max_revisions': 2}).max_revisions == 2
    payload = wizard(app)
    payload['budget'] = {'max_revisions': 3}
    with pytest.raises(ValueError, match='预算'):
        app.create(payload)
    assert app.studio.list_projects() == []
