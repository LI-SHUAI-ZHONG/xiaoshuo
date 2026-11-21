from copy import deepcopy

import pytest

from nw.materials import cast_demands as casting


def duty(**overrides):
    return {'id': 'handoff', 'slot': 'archive_keeper', 'need_ref': 'direction:choice',
            'need_quote': '核验被调换的旧册', 'event': '天亮前核验被调换的旧册',
            'obstacle': '密封账簿只有保管者可启封', 'action': '启封旧册交给监印员',
            'result': '监印员拿到带封记的原册', 'reuse_actor': None,
            'reason': '持有库房两份凭据的人才能完成这次交接', 'assessments': [], **overrides}


@pytest.mark.parametrize(('stage', 'field'), [('world_design', 'cast_demands'), ('character_design', 'cast_assignments')])
def test_native_model_schema_and_older_manifests_use_their_own_contract(stage, field):
    from nw.materials.phase_schema import schema
    current = schema(stage, [], cast_demand=True, allow_requests=False)['properties']['products']
    previous = schema(stage, [], allow_requests=False)['properties']['products']
    assert field in current['required'] and field in current['properties']
    assert field not in previous['properties']


def test_duties_derive_only_from_the_chosen_current_plot_and_handoff():
    cards = [{'card_id': key, 'kind': 'chapter', 'body': {'goal': key}} for key in ('old', 'next', 'third', 'elsewhere')]
    parent = {'root': {'card_id': 'root'}, 'approvals': [{'card_id': k} for k in ('root', 'old', 'next', 'third')],
              'chapters': [{'index': i} for i in (1, 2, 3)],
              'material_design': {'process_context': {'chapters': [{'index': i, 'card': k}
                  for i, k in enumerate(('old', 'next', 'third'), 1)], 'ids': {r['card_id']: r['card_id'] for r in cards}}}}
    ids = casting.source_card_ids(parent, cards, {'chapter': {'index': 1}})
    assert casting.source_card_ids(parent, cards, {'chapter': {'index': 1}}, 'volume') == ['next', 'third']
    context = {'scope': 'chapter', 'brief': {'text': '探索废墟'}, 'approved_cards': cards,
               'cast_source_cards': ids, 'cast_parent': {'choice': '核验被调换的旧册'},
               'chapter_openings': {'open:0': {'possible_next_pressure': '正本谁能启封？'}}}
    assert casting.source_options(context) == {'direction:choice': '核验被调换的旧册',
                                              'approved:next:goal': 'next', 'open:0:pressure': '正本谁能启封？'}
    assert casting.source_card_ids(parent, cards, {'chapter': {'index': 3}}) == []
    handoff = {'cast_prior_work': [{'evidence': [{'quote': '她交出了两把钥匙。'}],
                                    'designed_result': '另一人已经看懂钥匙刻痕'}],
               'chapter_changes': {'prior:1': {'holder': '监印员', 'claim': 'belief', 'entity_id': '账房',
                                                'predicate': '印是谁盖的', 'text': '保管者盖了印'}}}
    sources = casting.source_options({**context, **handoff})
    assert sources['prior-cast:0:span:0'] == '她交出了两把钥匙。'
    assert '监印员（belief）' in sources['prior:1:change']
    assert '另一人已经看懂钥匙刻痕' not in sources.values()


def test_reuse_or_new_is_decided_on_real_actor_evidence_before_assigning():
    sources = {'direction:choice': '须在天亮前核验被调换的旧册'}
    roster = {'clerk': {'want': '拿到原册解开误会'}, 'witness': {'boundaries': '不得触碰密封账簿'}}
    clerk = {'actor': 'clerk', 'field': 'want', 'quote': '拿到原册', 'reason': '有动机但仍无权启封'}
    witness = {'actor': 'witness', 'field': 'boundaries', 'quote': '不得触碰密封账簿', 'reason': '不可替保管人启封'}
    casting.validate_demands([duty(assessments=[clerk, witness])], sources, roster)
    casting.validate_demands([duty(reuse_actor='clerk', assessments=[clerk])], sources, roster)
    with pytest.raises(ValueError, match='须核对'):
        casting.validate_demands([duty(assessments=[clerk])], sources, roster)
    with pytest.raises(ValueError, match='真实人物卡'):
        casting.validate_demands([duty(assessments=[clerk, {**witness, 'quote': '账簿已公开'}])], sources, roster)
    with pytest.raises(ValueError, match='剧情前置'):
        casting.validate_demands([duty(need_ref='world:vault:rule', assessments=[clerk, witness])], sources, roster)


def test_assignments_tie_card_action_and_evidence_to_its_own_duty_and_keep_shared_slots():
    original = duty()
    second = duty(id='verify', event='验册后还原封签', action='交回封签两联', result='库内留存副联')
    products = {'world_design': {'products': {'cast_demands': [original, second]}}}
    body = {'scene_function': original['action'], 'casting': {k: original[k] for k in ('need_ref', 'need_quote')}}
    value = {'members': [{'key': 'keeper', 'body': body}], 'cast_assignments': [
        {'demand': 'handoff', 'actor': 'keeper'}, {'demand': 'verify', 'actor': 'keeper'}]}
    casting.validate_assignments(value, products, {})
    wrong = deepcopy(value)
    wrong['members'][0]['body']['scene_function'] = '向行人报糕点的价钱'
    with pytest.raises(ValueError, match='被分派的具体行动'):
        casting.validate_assignments(wrong, products, {})
    wrong = deepcopy(value)
    wrong['members'].append({'key': 'bystander', 'body': body})
    with pytest.raises(ValueError, match='分派'):
        casting.validate_assignments(wrong, products, {})
    wrong['cast_assignments'][1]['actor'] = 'bystander'
    with pytest.raises(ValueError, match='兼任'):
        casting.validate_assignments(wrong, products, {})
    prior = duty(reuse_actor='keeper')
    casting.validate_assignments({'members': [], 'cast_assignments': [{'demand': 'handoff', 'actor': 'keeper'}]},
                                 {'world_design': {'products': {'cast_demands': [prior]}}}, {})
    casting.validate_assignments({'members': [], 'cast_assignments': []},
                                 {'world_design': {'products': {'cast_demands': []}}}, {})


def test_approved_book_actor_is_reused_by_the_actual_chapter_desks(tmp_path):
    import json
    from nw.cards import read_card
    from nw.novel_flow import JobRequest, resume_job, start_job
    from nw.store import Store
    from nw.story_models import CardRef
    from nw.story_state import adopt_story
    from nw.task_models import Budget
    from nw.tasks import read_input_manifest
    from story_fixture import baseline
    from test_material_phase_flow import PhaseModel, template_catalog
    from test_material_workflow import choose
    from test_novel_flow import config

    template_catalog(tmp_path)
    provider = PhaseModel()
    with Store(tmp_path / 'reuse', create=True, test_mode=True) as store:
        store.init_project('核验封条')
        store.add_brief('由验印人借灯追查旧封条')
        adopt_story(store, baseline(), {})
        job = start_job(store, JobRequest('design', budget=Budget(32, 90000, 4000))).id
        assert resume_job(store, job, provider, config(store)).step == 'plan:book:confirm'
        waiting = resume_job(store, job, provider, config(store), choose)
        assert waiting.step == 'plan:chapter:confirm', waiting.reason
        packets = [json.loads(call[-1]['content']) for call in provider.calls]
        book_card, chapter_card = [p for p in packets if p.get('stage') == 'character_design']
        assert book_card['frozen_cast_demands'][0]['reuse_actor'] is None
        actor = chapter_card['frozen_cast_demands'][0]['reuse_actor']
        assert actor in {r['card_id'] for r in chapter_card['approved_cards']}
        result = resume_job(store, job, provider, config(store), choose)
        assert result.status == 'DONE', result.reason
        manifest = store.connection.execute('SELECT manifest_id FROM task_calls WHERE id=?',
                                            (result.outputs['proposal_id'],)).fetchone()[0]
        _, package = read_input_manifest(store, manifest)
        products = {r['stage']: r['products'] for r in package['material_work']['stages']}
        assert not products['character_design']['members']
        assert products['character_design']['cast_assignments'] == [{'demand': 'duty_0', 'actor': actor}]
        scene = result.outputs['application']['chapters'][0]['scenes'][0]['scene_ref']
        assert read_card(store, CardRef(**scene))['body']['pov'] == actor
