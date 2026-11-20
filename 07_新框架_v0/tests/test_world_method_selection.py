"""World methods are filtered by actual genre, evidenced scope, live prerequisites and demand."""
from copy import deepcopy

import pytest

from ai_world_method_fixture import TAXON, available_method
from nw.production_methods.policy import normalize
from nw.production_methods.runtime import packet
from nw.production_methods.selection import build_target, check_bindings, finalize
from nw.production_methods.inputs import registry
from nw.production_methods.sources import MethodReader
from nw.production_methods.world_selection import needs, parent_design, verify_context
from nw.task_models import content_sha256


def stage(name, products):
    return {'stage': name, 'task_id': 'test-task-' + name, 'products': products, 'sha256': content_sha256(products)}


def request():
    # The actual selection is mystery, even when a previous wizard preference said fantasy.
    package = {'scope': 'book', 'brief': {'project_id': 'project-1', 'version': 1,
               'text': '调查渡口放行记录被涂改的案件。', 'constraints': '核验依据可被他人复查'},
               'production_method_policy': normalize({'tasks': ['world_rules'], 'world_selection': 'ai',
                                                      'type_ids': ['GENRE_QIHUAN']})}
    products = {'type_selection': stage('type_selection', {'selection': [{'id': TAXON, 'basis': '以独立旁证复查渡口记录。'}]}),
                'type_adaptation': stage('type_adaptation', {'adaptations': [
                    {'id': 'record_check', 'type_refs': [TAXON], 'parameters': {'evidence': '岸亭回执须记号核验。'},
                     'limits': ['仅凭蜡印无法放行。']}]})}
    return package, products


def test_offer_owns_current_method_and_evidence_but_preserves_historical_selection(tmp_path, monkeypatch):
    library, source = available_method(tmp_path, monkeypatch)
    reader = MethodReader(tmp_path)
    package, products = request()
    target = build_target(reader, package, 'world_design', products)
    [first] = target['candidates']
    from nw.studio.method_recommendations import recommendations
    wizard = recommendations(reader, 'world', [TAXON], [])['recommendations']
    assert [(r['id'], r['version']) for r in wizard] == [(first['method']['id'], first['method']['version'])]
    assert not recommendations(reader, 'world', ['GENRE_QIHUAN'], [])['recommendations']
    assert first['adaptation_indices'] == [0]
    mixed = deepcopy(products)
    mixed['type_selection']['products']['selection'].append({'id': 'GENRE_QIHUAN', 'basis': '以超自然边界约束魔法。'})
    mixed['type_adaptation']['products']['adaptations'].append(
        {'type_refs': ['GENRE_QIHUAN'], 'parameters': {'magic': '魔法须耗用护符。'}, 'limits': []})
    mixed = {k: stage(k, r['products']) for k, r in mixed.items()}
    combined = build_target(reader, package, 'world_design', mixed)
    assert combined['adaptation_indices'] == [0, 1] and combined['candidates'][0]['adaptation_indices'] == [0]
    assert first['method']['id'] == source['id'] and first['method']['body']['non_applicability']
    assert first['source_type_match']['type_ids'] == [TAXON] and target['adaptation_indices'] == [0]
    pending = {'target': target, 'selected': [], 'decision': None}
    sent = packet(pending, [])
    assert sent['production_methods'] == [first] and sent['production_method_decision'] is None
    final = finalize(pending, {'_method_applications': [{'method_id': source['id']}]})
    assert final['selected'] == [first] and final['decision'] == {'actor': 'ai', 'method_ids': [source['id']]}
    for apps in ([], [{'method_id': 'unknown'}], [{'method_id': source['id']}] * 2):
        with pytest.raises(ValueError, match='PROJECT_METHOD'):
            finalize(pending, {'_method_applications': apps})
    revised = deepcopy(source['body'])
    revised['title'] += '（核验补充）'
    library.save_method({'expected_version': 1, 'body': revised}, source['id'])
    library.review_method(source['id'], {'version': 2, 'decision': 'approve', 'note': '[FAKE] 已核对原作。'})
    second = build_target(reader, package, 'world_design', products)['candidates']
    assert [v['method']['version'] for v in second] == [2]
    reader.verify(first['method'], require_current=False)
    with pytest.raises(ValueError, match='STALE_PROJECT_METHOD'):
        reader.verify(first['method'])
    changed = deepcopy(products['type_adaptation']['products'])
    changed['adaptations'][0]['limits'][0] = '抵岸前须独立取得第三份记录。'
    now = {**products, 'type_adaptation': stage('type_adaptation', changed)}
    with pytest.raises(ValueError, match='STALE_PROJECT_METHOD'):
        check_bindings(target, registry(package, now, ai_world=True))
    session = {'scope': 'book', 'context': {'brief': package['brief']}, 'production_method_policy': package['production_method_policy']}
    with pytest.raises(ValueError, match='STALE_PROJECT_METHOD'):
        verify_context(final, session, now)


def test_missing_actual_selection_or_matching_adaptation_stops_before_query(tmp_path):
    package, products = request()
    reader = MethodReader(tmp_path)
    for changed in ({}, {'type_selection': products['type_selection']},
                    {**products, 'type_selection': stage('type_selection', {'selection': [{'id': 'invented', 'basis': '悬疑'}]})},
                    {**products, 'type_adaptation': stage('type_adaptation', {'adaptations': [
                        {'id': 'different', 'type_refs': ['GENRE_QIHUAN'], 'limits': ['另行设计']} ]})}):
        with pytest.raises(ValueError, match='METHOD_DESIGN_REQUIRED'):
            build_target(reader, package, 'world_design', changed)
    assert normalize({'tasks': ['world_rules'], 'world_selection': 'ai'})['type_ids'] == []


def test_rank_all_eligible_methods_before_freezing_window_and_only_bind_selected_ones(tmp_path, monkeypatch):
    _, source = available_method(tmp_path, monkeypatch)
    package, products = request()
    reader = MethodReader(tmp_path)
    # Use the same genuinely reviewed example as the input shape to isolate ranking from storage.
    rows = [{**source, 'id': 'method-' + str(i).zfill(2), 'body': {**source['body'],
             'title': '岸亭回执须记号核验' if i == 48 else '边界方法'}} for i in range(49)]
    pin = reader.snapshot(source)
    monkeypatch.setattr(reader, 'approved', lambda: rows)
    monkeypatch.setattr(reader, 'world_source', lambda row, types: ({**pin, 'id': row['id'], 'body': row['body']},
                        {'level': 'main', 'type_ids': [TAXON], 'source_type_ids': [TAXON]}))
    target = build_target(reader, package, 'world_design', products)
    assert target['candidate_total'] == len(target['candidates']) == 49 and target['page_size'] == 12
    sent = packet({'target': target, 'selected': [], 'decision': None}, [])['production_methods']
    assert sent == target['candidates'][:12]
    assert [c['method']['id'] for c in target['candidates'][1:]] == [r['id'] for r in rows[:-1]]
    assert target['candidates'][0]['method']['id'] == 'method-48'
    ids = ['method-03', 'method-48']
    chosen = finalize({'target': target, 'selected': [], 'decision': None},
                      {'_method_applications': [{'method_id': key} for key in ids]})
    assert [r['method']['id'] for r in chosen['selected']] == ids


def test_parent_reuse_changes_when_only_its_project_design_constraint_changes():
    package, previous = request()
    demand = {'brief': package['brief'], **{k: v['products'] for k, v in previous.items()}}
    context = {'demand': demand, 'type_ids': [TAXON], 'adaptation_indices': [0]}
    member = {'key': 'passage', 'kind': 'world', 'body': {'title': '关卡', 'rule': '双证放行', 'limits': '冲突扣验'}}
    entry = {'id': 'delivery', 'approved_parent': {'card_id': 'outline', 'version': 2},
             'world_design_basis': {'needs': needs(demand, [TAXON], [0]), 'members': [member]}}
    assert parent_design(context, [entry]) == {'parent_deliveries': ['delivery'], 'approved_world_members': [member]}
    altered = deepcopy(context)
    altered['demand']['type_adaptation']['adaptations'][0]['limits'][0] = '核验误差时须查见证人，而非暂停。'
    assert parent_design(altered, [entry]) == {}


def test_replacing_one_world_card_preserves_the_other_card_in_the_same_handoff():
    from nw.production_methods.handoff import retained_world

    original = {'id': 'book-receipt', 'world_design_basis': {'members': [{'key': 'permit'}, {'key': 'tide'}]},
                'output': {'placements': [{'path': ['members', i, 'body', field], 'value': '原书纲规则'}
                                          for i in (0, 2) for field in ('rule', 'limits')]}}
    assert retained_world(original, {'permit', 'tide'}) is original
    remaining = retained_world(original, {'tide'})
    assert remaining['parent_delivery_id'] == original['id'] and remaining['id'] != original['id']
    assert [c['key'] for c in remaining['world_design_basis']['members']] == ['tide']
    assert [p['path'] for p in remaining['output']['placements']] == [['members', 2, 'body', field] for field in ('rule', 'limits')]
    assert retained_world(original, set()) is None
