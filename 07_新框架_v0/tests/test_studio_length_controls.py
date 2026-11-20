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


@pytest.mark.parametrize('tier,low,high', [
    (300_000, 200_000, 399_999), (500_000, 400_000, 749_999),
    (1_000_000, 750_000, 1_249_999), (1_500_000, 1_250_000, 1_749_999),
    (2_000_000, 1_750_000, 2_250_000),
])
def test_tier_recommendation_and_finish_share_closed_boundaries(tier, low, high):
    from nw.length_settings import book_word_range, nearest_word_tier
    from nw.studio.production_length import verify_finish_length
    assert book_word_range(tier) == (low, high)
    assert nearest_word_tier(low) == nearest_word_tier(high) == tier
    assert nearest_word_tier(low - 1) != tier and nearest_word_tier(high + 1) != tier
    ready = {'length_mode': 'tiered', 'minimum_words': low, 'maximum_words': high,
             'chapters': [{'index': 1, 'accepted_words': 2000}, {'index': 2, 'accepted_words': 2500}]}
    for valid in (low, tier, high):
        verify_finish_length({**ready, 'accepted_words': valid})
    for invalid in (low - 1, high + 1):
        with pytest.raises(ValueError, match='档位'):
            verify_finish_length({**ready, 'accepted_words': invalid})
    for invalid in (1999, 2501):
        with pytest.raises(ValueError, match='第2章'):
            verify_finish_length({**ready, 'accepted_words': tier, 'chapters': [{'index': 2, 'accepted_words': invalid}]})


def test_upgrading_a_project_uses_current_tier_choice_and_preserves_old_brief(app):
    raw = {**wizard(app), 'target_words': 51000, 'chapter_count': 44, 'volume_count': 2,
           'chapter_target_words': 1200, 'scene_target_words': 420, 'word_tolerance_pct': 4}
    novel = app.create(raw)['novel']
    plan = app.configure_length(novel['id'], {'length_mode': 'tiered', 'target_words': 500000})['length_plan']
    assert (plan['minimum_words'], plan['maximum_words'], plan['chapter_min_words'], plan['chapter_max_words']) == (
        400000, 749999, 2000, 2500)
    actual = app.db.get(novel['id'])['wizard']
    assert actual['volume_count'] == 2
    assert not set(('chapter_count', 'chapter_target_words', 'scene_target_words', 'word_tolerance_pct')) & actual.keys()
    assert governance(actual)['plot_design']['length_auto']
    with pytest.raises(ValueError, match='篇幅'):
        app.configure_length(novel['id'], {'target_words': 51000})
    with pytest.raises(ValueError, match='固定配额'):
        app.configure_length(novel['id'], {'chapter_count': 44})
    with app.open_store(novel) as store:
        assert '51000' in store.briefs()[0].text
    assert app.db.get(novel['id'])['wizard']['target_words'] == 500000
    cleared = app.configure_length(novel['id'], {'target_words': None})['length_plan']
    assert cleared['length_mode'] == 'tiered' and cleared['effective_target_words'] is None


def test_tier_suggestion_is_frozen_by_the_library_and_explicit_choice_wins(app, monkeypatch):
    from nw.studio.production_inputs import freeze_wizard, governance
    raw = {**wizard(app), 'length_mode': 'tiered', 'length_recommendation': {'recommended_tier': 2_000_000}}
    votes = {'types': raw['genre_ids'], 'recommended_tier': 500000, 'counts': {'500000': 2},
             'sample_count': 2, 'eligible_count': 2, 'outside_count': 0}
    monkeypatch.setattr(app.library, 'recommend_length', lambda types: dict(votes))
    saved = freeze_wizard(raw, app.library)
    assert saved['length_recommendation'] == votes
    assert governance(saved)['plot_design']['length_recommendation'] == votes
    explicit = freeze_wizard({**raw, 'target_words': 300000}, app.library)
    assert 'length_recommendation' not in governance(explicit)['plot_design']
    assert governance(explicit)['plot_design']['length_policy']['target_words'] == 300000


def test_finished_manuscript_within_tier_can_close_before_the_estimated_chapter_count(app):
    from nw.acceptance import accept_batch
    from nw.config import Config
    from nw.models import Run
    from nw.planning import plan_input, propose_plan
    from nw.store import now
    from nw.story_state import current_head
    from nw.studio.production import ProductionService
    from nw.task_models import Budget, canonical
    from story_fixture import draft_for, proposal
    from test_planning import Planner, apply
    from test_studio_length_recommendations import reference

    app = ProductionService(app.studio, app.library, test_mode=True)
    form = {**wizard(app), 'length_mode': 'tiered'}
    reference(app.library, '证据。' * 100000, '隔离参考样本', form['genre_ids'])
    novel = app.create(form)['novel']
    assert app.detail(novel['id'])['length_plan']['minimum_words'] is None
    with app.open_store(novel) as store:
        planner = Planner('book')
        for candidate in planner.output['candidate_cards']:
            candidate['body']['length_plan'] = {'target_words': 300000, 'chapter_count': 137, 'reason': '[FAKE] 长篇证据调查'}
        route = Config('fake', 'http://localhost', 'test', '', 5, {}, store.directory, source_driven=False)
        job_row = store.connection.execute('SELECT request_json FROM novel_jobs WHERE id=?', (novel['job_id'],)).fetchone()
        inputs = {'plot_design': json.loads(job_row[0])['governance_inputs']['plot_design']}
        direction = propose_plan(store, 1, 'book', planner, route, Budget(1, 64000, 4000), governance_inputs=inputs)
        frozen = plan_input(store, direction.id)[1]
        assert frozen['length_context']['length_recommendation']['recommended_tier'] == 300000
        assert frozen['length_context']['length_recommendation']['sample_count'] == 1
        apply(store, direction)
        head = current_head(store)
        requests = []
        lengths = [2000, 2200, 2500] * 30
        for index, size in enumerate(lengths, 1):
            chapter = store.add_chapter(index, f'证据 {index}')
            scene = store.add_scene(chapter.id, 1, '{}')
            draft = draft_for(store, scene.id, '[FAKE]' + '档' * (size - 7) + '。')
            requests.append(proposal(store, head, draft, []))
            snapshot = {'messages': [{'content': canonical({'draft': {'id': draft.id}})}]}
            store.add_run(Run('review-' + scene.id, scene.id, 'review', 'author', 'test-review', '{}',
                              canonical(snapshot), '{}', '{"recommendation":"pass"}', 'complete', '{}', now(), now()))
        accept_batch(store, requests, head, 'approve-isolated-manuscript')
    summary = app.detail(novel['id'])['length_plan']
    assert summary['effective_target_words'] == 300000 and summary['effective_chapter_count'] == 137
    assert summary['accepted_words'] == sum(lengths) and summary['remaining_words'] == 0
    assert len(summary['chapters']) == 90 and summary['delta_words'] == 0
    assert app.finish(novel['id'])['status'] == 'DONE'
    text, _ = app.export(novel['id'])
    assert '第90章 证据 90' in text
