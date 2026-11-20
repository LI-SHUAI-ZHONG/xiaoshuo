"""[FAKE] Verify a reference novel becomes a method, then a different project's world and scenes."""
import json

import pytest

from ai_world_method_fixture import (
    BRIEF, FOG_BRIEF, FOG_LIMIT, FOG_RULE, LIMIT, RULE, SOURCE, TAXON, WorldModel, available_method, source_methods,
)
from nw.cards import read_card
from nw.materials.evidence import scene_checks, scene_materials
from nw.materials.phase_projection import verify_chain
from nw.materials.phase_routes import product_ref
from nw.novel_flow import resume_job
from nw.novel_store import JobRequest, start_job
from nw.production_methods.policy import normalize
from nw.production_methods.selection import verify_sources
from nw.store import Store
from nw.story_models import CardRef
from nw.story_state import adopt_story
from nw.task_models import Budget
from project_methods_fixture import config, template_catalog
from story_fixture import baseline
from test_project_methods import approve_direction, start


def new_project(store, brief):
    store.init_project('[FAKE] 临川渡')
    store.add_brief(brief)
    adopt_story(store, baseline(), {})


def policy():
    return normalize({'tasks': ['world_rules'], 'type_ids': [TAXON], 'world_selection': 'ai'})


def stages(session):
    return {row['stage']: row for row in session['stages']}


def packets(model, stage):
    return [payload for messages in model.calls if (payload := json.loads(messages[-1]['content'])).get('stage') == stage]


def finish_design(store, model, scope='book', parent=None):
    job, outcome = start(store, model, scope, parent, policy())
    assert outcome.status == 'WAITING', outcome.reason
    assert outcome.outputs['gate'].get('kind') != 'production_method_selection'
    complete = approve_direction(store, job, model, outcome)
    assert complete.status == 'DONE', complete.reason
    return complete


@pytest.mark.parametrize(('brief', 'rule', 'limit', 'record'), [
    (BRIEF, RULE, LIMIT, '潮刻'),
    (FOG_BRIEF, FOG_RULE, FOG_LIMIT, '岸亭回执'),
], ids=['visible-tide', 'permanent-fog'])
def test_ai_uses_the_projects_actual_prior_needs_and_preserves_the_world_after_reopen(
        tmp_path, monkeypatch, brief, rule, limit, record):
    template_catalog(tmp_path)
    library, method = available_method(tmp_path, monkeypatch)
    path = tmp_path / '[FAKE]-world'
    model = WorldModel()
    with Store(path, create=True, test_mode=True) as store:
        new_project(store, brief)
        complete = finish_design(store, model)
        application = complete.outputs['application']
        session = application['material_design']['work_session']
        by_stage = stages(session)
        world = by_stage['world_design']
        [packet] = packets(model, 'world_design')
        assert not packet['approved_cards']
        assert packet['production_method_selection']['mode'] == 'ai'
        [candidate] = packet['production_methods']
        assert candidate['inputs']['task']['value']['text'] == brief
        for key, source_stage in [('genre', 'type_selection'), ('approach', 'type_adaptation')]:
            assert candidate['inputs'][key]['ref'] == product_ref(by_stage[source_stage])
            assert candidate['inputs'][key]['value'] == by_stage[source_stage]['products']
        pin = candidate['method']
        assert pin['id'] == method['id'] and pin['version'] == 1
        assert pin['structure_origin']['book_id'] == method['structure_origin']['book_id']
        assert len(pin['instance']['events']) >= 2
        assert all(SOURCE[e['start']:e['end']] == e['quote'] for e in pin['body']['evidence'])
        plan = world['production_methods']
        assert [v['method']['id'] for v in plan['selected']] == [method['id']]
        assert plan['decision']['actor'] == 'ai' and plan['decision']['method_ids'] == [method['id']]
        [adoption] = world['products']['_method_applications']
        assert adoption['design_basis'] == [
            {'kind': 'type_adaptation', 'path': ['adaptations', 0, 'parameters', 'investigation']}]
        [output] = adoption['outputs']
        actual = {tuple(row['path']): row['value'] for row in output['placements']}
        assert actual == {('members', 0, 'body', 'rule'): rule, ('members', 0, 'body', 'limits'): limit}
        [plot] = by_stage['plot_design']['products']['_method_receipts']
        assert plot['placements'] and all(record in p['value'] for p in plot['placements'])
        assert not any(name in rule + limit for name in ('暮塔', '影碑', '灯签', '金铃'))
        cards = [read_card(store, CardRef(r['card_id'], r['version'])) for r in application['approvals']]
        assert any(c['kind'] == 'world' and c['body']['rule'] == rule and c['body']['limits'] == limit for c in cards)
        proposal = complete.outputs['proposal_id']

    with Store(path, test_mode=True) as reopened:
        saved = reopened.connection.execute('SELECT mapping_json FROM plan_applications WHERE proposal_id=?',
                                            (proposal,)).fetchone()
        restored = json.loads(saved[0])['material_design']['work_session']
        verify_chain(restored)
        verify_sources(reopened, restored)
        assert stages(restored)['world_design']['production_methods'] == plan
        library.review_book(pin['structure_origin']['book_id'], {'decision': 'reject', 'note': '[FAKE] 来源撤回'})
        with pytest.raises(ValueError, match='STALE_PROJECT_METHOD'):
            verify_sources(reopened, restored)


@pytest.mark.parametrize(('approve', 'taxon'), [(False, TAXON), (True, 'GENRE_QIHUAN')])
def test_missing_approved_evidence_or_mismatched_actual_genre_stops_world_invention(
        tmp_path, monkeypatch, approve, taxon):
    template_catalog(tmp_path)
    available_method(tmp_path, monkeypatch, approve=approve)
    with Store(tmp_path / '[FAKE]-missing', create=True, test_mode=True) as store:
        new_project(store, BRIEF)
        model = WorldModel(taxon=taxon)
        _, outcome = start(store, model, policy=policy())
        assert outcome.status == 'BLOCKED' and 'METHOD_DESIGN_REQUIRED' in outcome.reason, outcome.reason
        assert not packets(model, 'world_design')
        assert not store.connection.execute('SELECT 1 FROM plan_applications').fetchone()


@pytest.mark.parametrize('invalid', ['label', 'verbatim', 'unrelated_basis', 'omit_receipt'])
def test_false_attribution_and_dropped_handoff_cannot_publish_project_world(tmp_path, monkeypatch, invalid):
    template_catalog(tmp_path)
    available_method(tmp_path, monkeypatch)
    with Store(tmp_path / '[FAKE]-invalid', create=True, test_mode=True) as store:
        new_project(store, BRIEF)
        model = WorldModel(invalid=invalid)
        model.omit_receipt = invalid == 'omit_receipt'
        _, outcome = start(store, model, policy=policy())
        assert outcome.status == 'BLOCKED' and 'PROJECT_METHOD' in outcome.reason, outcome.reason
        assert not store.connection.execute('SELECT 1 FROM plan_applications').fetchone()


@pytest.mark.parametrize('scopes', [('book', 'chapter'), ('book',)], ids=['book-and-chapter', 'book-only'])
def test_ai_world_from_full_text_reaches_chapter_writer_and_independent_review(tmp_path, monkeypatch, scopes):
    template_catalog(tmp_path)
    _, method = available_method(tmp_path, monkeypatch, scopes=scopes)
    with Store(tmp_path / '[FAKE]-chapter', create=True, test_mode=True) as store:
        new_project(store, FOG_BRIEF)
        model = WorldModel()
        book = finish_design(store, model)
        chapter = finish_design(store, model, 'chapter', book.outputs['proposal_id'])
        application = chapter.outputs['application']
        session = application['material_design']['work_session']
        scene_record = stages(session)['scene_design']
        scene = application['chapters'][0]['scenes'][0]['scene_id']
        assert session['production_method_parents']
        if scopes == ('book',):
            assert not stages(session)['world_design']['products'].get('_method_applications')
        assert all('岸亭回执' in p['value'] for receipt in scene_record['products']['_method_receipts']
                   for p in receipt['placements'])
        checks = [c for c in scene_checks(scene_materials(store, scene)) if c['id'].startswith('method:')]
        assert checks and all(c['production_method']['version'] == method['version'] for c in checks)
        job = start_job(store, JobRequest('write', scene_ids=[scene], budget=Budget(20, 200000, 6000, 0)))
        result = resume_job(store, job.id, model, config(store))
        assert result.status == 'WAITING', result.reason
        reviews = [p for m in model.calls if 'material_review' in (p := json.loads(m[-1]['content']))]
        assert reviews and '岸亭回执' in reviews[-1]['draft']['text']
        assert any(row['id'] == check['id'] for row in reviews[-1]['material_review']['checks'] for check in checks)
        result = resume_job(store, job.id, model, config(store),
                            lambda *_: {'action': 'accept', 'reason': '[FAKE] 核对现场证据与来源。'})
        assert result.status == 'DONE' and store.list('accepted'), result.reason


@pytest.mark.parametrize('change', ['new_requirement', 'expose_private'])
def test_chapter_cannot_reuse_a_changed_requirement_or_overwrite_parent_visibility(tmp_path, monkeypatch, change):
    template_catalog(tmp_path)
    available_method(tmp_path, monkeypatch, scopes=('book',))
    with Store(tmp_path / '[FAKE]-changed', create=True, test_mode=True) as store:
        new_project(store, BRIEF)
        model = WorldModel(invalid=change)
        book = finish_design(store, model)
        if change == 'new_requirement':
            store.add_brief(FOG_BRIEF)
        before = len(packets(model, 'world_design'))
        _, outcome = start(store, model, 'chapter', book.outputs['proposal_id'], policy())
        assert outcome.status == 'BLOCKED', outcome.reason
        if change == 'new_requirement':
            assert 'METHOD_DESIGN_REQUIRED' in outcome.reason and len(packets(model, 'world_design')) == before
        else:
            assert 'PROJECT_METHOD' in outcome.reason and len(packets(model, 'world_design')) > before
        assert not store.list('draft')


def test_changed_chapter_uses_new_rule_without_assigning_the_superseded_rule_to_its_scenes(tmp_path, monkeypatch):
    template_catalog(tmp_path)
    available_method(tmp_path, monkeypatch)
    with Store(tmp_path / '[FAKE]-redesign', create=True, test_mode=True) as store:
        new_project(store, BRIEF)
        model = WorldModel()
        book = finish_design(store, model)
        store.add_brief(FOG_BRIEF)
        chapter = finish_design(store, model, 'chapter', book.outputs['proposal_id'])
        session = chapter.outputs['application']['material_design']['work_session']
        assert any(p['value'] == RULE for entry in session['production_method_parents']
                   for p in entry['output']['placements'])
        assert stages(session)['world_design']['products']['members'][0]['body']['rule'] == FOG_RULE
        for stage in ('plot_design', 'scene_design'):
            incoming = packets(model, stage)[-1]['method_handoffs']
            active_rules = [p['value'] for item in incoming for p in item['output']['placements']
                            if p['path'][-1] == 'rule']
            assert active_rules == [FOG_RULE]
        scene = chapter.outputs['application']['chapters'][0]['scenes'][0]['scene_id']
        checks = [c for c in scene_checks(scene_materials(store, scene)) if c['id'].startswith('method:')]
        assert checks and all('岸亭回执' in c['binding']['observable'] for c in checks)


@pytest.mark.parametrize('choice', ['unusable', 'first_page_gap', 'unoffered'])
def test_only_offered_applicable_world_methods_can_publish_after_paging(tmp_path, monkeypatch, choice):
    from nw.production_methods import selection

    template_catalog(tmp_path)
    _, methods = source_methods(tmp_path, monkeypatch, two_methods=True)
    real_target = selection.build_world_target

    def single_per_page(*args, **kwargs):
        return {**real_target(*args, **kwargs), 'page_size': 1}

    monkeypatch.setattr(selection, 'build_world_target', single_per_page)
    model = WorldModel(invalid=choice)
    model.known_ids = {method['id'] for method in methods}
    assert len(model.known_ids) == 2
    with Store(tmp_path / '[FAKE]-pages', create=True, test_mode=True) as store:
        new_project(store, '[FAKE] 悬疑。保护证人匿名，核验授权时不可留下证人行踪。' if choice == 'unusable' else FOG_BRIEF)
        job, result = start(store, model, policy=policy())
        pages = packets(model, 'world_design')
        visible = [[item['method']['id'] for item in page['production_methods']] for page in pages]
        if choice == 'unoffered':
            assert result.status == 'BLOCKED' and '本页实际送达的候选' in result.reason, result.reason
            assert len(visible) == 1 and len(visible[0]) == 1
        else:
            assert [p['production_method_selection']['page'] for p in pages] == [1, 2], result.reason
            assert len(visible[0]) == len(visible[1]) == 1 and visible[0] != visible[1]
            assert {visible[0][0], visible[1][0]} == model.known_ids
            if choice == 'first_page_gap':
                assert result.status == 'WAITING' and result.outputs['gate'].get('kind') != 'production_method_selection', result.reason
                done = approve_direction(store, job, model, result)
                assert done.status == 'DONE', done.reason
                world = stages(done.outputs['application']['material_design']['work_session'])['world_design']
                assert world['production_methods']['decision']['method_ids'] == visible[1]
                return
            assert result.status == 'BLOCKED' and 'METHOD_DESIGN_REQUIRED' in result.reason, result.reason
            assert '证人行踪' in result.reason and '匿名证人' in result.reason
        assert not store.connection.execute('SELECT 1 FROM plan_applications').fetchone()


def test_book_rule_survives_approved_volume_and_reaches_a_grandchild_chapter(tmp_path, monkeypatch):
    template_catalog(tmp_path)
    _, method = available_method(tmp_path, monkeypatch, scopes=('book',))
    with Store(tmp_path / '[FAKE]-volume', create=True, test_mode=True) as store:
        new_project(store, BRIEF)
        model = WorldModel()
        book = finish_design(store, model)
        volume = finish_design(store, model, 'volume', book.outputs['proposal_id'])
        model.chapter_index = 2
        chapter = finish_design(store, model, 'chapter', volume.outputs['proposal_id'])
        grandchild = chapter.outputs['application']['material_design']['work_session']
        for approved in [volume, chapter]:
            session = approved.outputs['application']['material_design']['work_session']
            world = stages(session)['world_design']
            assert world['production_methods']['target']['selection_mode'] == 'inherit_world'
            assert world['products']['members'][0]['body']['rule'] == RULE
            verify_chain(session)
            verify_sources(store, session)
        [inherited] = grandchild['production_method_parents']
        assert inherited['method']['id'] == method['id'] and inherited['method']['version'] == method['version']
        [scene_use] = stages(grandchild)['scene_design']['products']['_method_receipts']
        assert scene_use['id'] == inherited['id'] and '潮刻' in scene_use['scene_guidance'][0]['observable']


def test_active_six_source_workflow_creates_world_while_unproven_network_history_waits(tmp_path, monkeypatch):
    import test_material_world_conversion_flow as six_source
    from test_material_world_history_flow import TURN

    monkeypatch.setattr(six_source, 'SELECTED_GENRE', (TAXON, '悬疑'))
    [(_, dynamic_id)] = six_source._catalog(tmp_path, monkeypatch, (TURN,)).values()
    _, method = available_method(tmp_path, monkeypatch)
    with Store(tmp_path / '[FAKE]-six-source', create=True, test_mode=True) as store:
        new_project(store, FOG_BRIEF)
        model = WorldModel()
        done = finish_design(store, model)
        session = done.outputs['application']['material_design']['work_session']
        [world] = packets(model, 'world_design')
        assert not world['approved_cards']
        assert session['context'][TURN.policy_key] == TURN.policy
        assert world['production_method_selection']['mode'] == 'ai'
        assert dynamic_id in session['context']['world_network_bases']
        assert 'network_waiting' not in world
        assert dynamic_id not in world['world_network_prerequisites'] and dynamic_id not in world['readable_source_ids']
        record = stages(session)['world_design']
        assert record['production_methods']['decision']['method_ids'] == [method['id']]
        assert record['products']['members'][0]['body']['rule'] == FOG_RULE
        verify_chain(session)
        verify_sources(store, session)
