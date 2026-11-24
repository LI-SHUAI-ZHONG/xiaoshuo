from dataclasses import asdict

from nw.cards import decide_card, link_cards, read_card, save_card
from nw.context.story import StoryProvider, build_story_context, scene_scope
from nw.materials.step_guard import build_continuity_ledger
from nw.store import Store
from nw.story_models import CardRef
from nw.story_state import adopt_story, replay
from nw.task_models import canonical, content_sha256
from story_fixture import baseline


def _approved(store, kind, ident, body):
    ref = save_card(store, {'card_id': ident, 'kind': kind, 'origin': 'author', 'body': body}, None)
    decision = decide_card(store, ref, 'approved', '通过剧情设计')
    return {**asdict(ref), 'decision_id': decision.id}


def _stage(ident, old, new, chapter):
    return {'op': 'set', 'entity_id': ident, 'predicate': 'promise_stage', 'holder': 'WORLD', 'claim': 'fact',
            'expected_old': old, 'new_value': new, 'story_order': chapter, 'disclosure_order': [chapter, 1, 0],
            'evidence': [{'draft_id': f'draft-{chapter}', 'text_sha256': 'a' * 64, 'start': 0, 'end': 3}]}


def _archive(store, root, card, ident, row, *, proof=True):
    products = {'promise_plan': [row]}
    plot = {'stage': 'plot_design', 'task_id': ident + '-plot', 'products': products,
            'sha256': content_sha256(products) if proof else 'b' * 64}
    decision = root['decision_id']
    mapping = {'root': {k: root[k] for k in ('card_id', 'version')}, 'decision_id': decision,
               'approvals': [root, card], 'material_design': {
                   'process_context': {'ids': {'old-promise': card['card_id']}},
                   'work_session': {'stages': [plot]}}}
    with store.connection:
        store.connection.execute('INSERT INTO input_manifests VALUES (?, ?, ?, ?)', (ident, '{}', '{}', 'unused'))
        store.connection.execute('INSERT INTO budgets(id, limits_json) VALUES (?, ?)', (ident, '{}'))
        store.connection.execute("""INSERT INTO task_calls(id,project_id,kind,manifest_id,manifest_json,request_json,
            messages_json,budget_id,root_id,attempt,status,validation,started_at)
            VALUES (?,?,'plan',?,'{}','{}','[]',?,?,1,'FINISHED','VALID','test')""",
                                 (ident, store.project().id, ident, ident, ident))
        store.connection.execute('INSERT INTO plan_applications VALUES (?, ?, ?)', (ident, decision, canonical(mapping)))


def test_active_approved_schedule_and_actual_selected_progress(tmp_path):
    from nw.materials.promise_continuity import approved_promise_snapshot

    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        store.init_project('隔离伏笔校验')
        pending = _approved(store, 'promise', 'sealed-door', {'title': '封门', 'setup': '空封条', 'payoff': '仓门在空屋里'})
        future = _approved(store, 'promise', 'future', {'title': '另一条线', 'setup': '开闸', 'payoff': '上游无水'})
        root = _approved(store, 'plot', 'book-root', {'title': '全书', 'conflict': '查档', 'consequence': '失去工作'})
        stale = _approved(store, 'plot', 'stale-root', {'title': '旧版', 'conflict': '查档', 'consequence': '放弃'})
        archived = {'id': 'old-local', 'promise': 'old-promise', 'status': 'paid_off', 'plant_chapter': 1,
                    'payoff_chapter': 6, 'payoff_event': 'investigate', 'payoff_window': {'min_offset': 2, 'max_offset': 4}}
        _archive(store, stale, pending, 'stale', {**archived, 'payoff_chapter': 2})
        _archive(store, root, pending, 'invalid', {**archived, 'payoff_chapter': 3}, proof=False)
        _archive(store, root, pending, 'book', archived)
        approvals = [pending, future, root]
        cards = [read_card(store, CardRef(row['card_id'], row['version'])) for row in approvals]
        accepted = [_stage('sealed-door', None, 'planted', 2), _stage('sealed-door', 'planted', 'awake', 4)]
        discarded = _stage('sealed-door', 'awake', 'paid_off', 7)

        def snapshot(ops):
            return approved_promise_snapshot(store, approvals, cards, replay({'facts': []}, ops), ops)

        by_id = {row['card_id']: row for row in snapshot(accepted)}
        assert by_id['sealed-door']['accepted_stage'] == 'awake'
        assert by_id['sealed-door']['planted_chapter'] == 2
        assert by_id['sealed-door']['state_evidence'][0]['draft_id'] == 'draft-4'
        assert by_id['sealed-door']['schedule']['payoff_chapter'] == 6
        assert 'payoff_event' not in by_id['sealed-door']['schedule']
        assert by_id['future']['accepted_stage'] is None
        payoff = {row['card_id']: row for row in snapshot([*accepted, discarded])}['sealed-door']
        assert payoff['accepted_stage'] == 'paid_off'
        context = {'promise_continuity': [payoff], 'current_chapter': 9}
        guard = build_continuity_ledger('plot_design', {}, [], context)['foreshadow_reminder']
        assert guard['lifecycle_counts']['paid_off'] == 1
        assert guard['resolved'] == ['sealed-door']
        assert not guard['due_this_scene'] and not guard['overdue_warnings']


def test_unaccepted_candidate_cannot_replace_lifecycle_and_local_event_does_not_travel():
    products = {'plot_design': {'products': {'promise_plan': [
        {'id': 'candidate', 'promise': 'confirmed', 'status': 'paid_off', 'payoff_event': 'check'},
        {'id': 'brand-new', 'promise': 'new', 'status': 'planted', 'payoff_event': 'check'},
    ]}}}
    context = {'promise_continuity': [
        {'card_id': 'confirmed', 'title': '封门', 'version': 1, 'accepted_stage': 'planted', 'planted_chapter': 2,
         'schedule': {'payoff_chapter': 6}},
        {'card_id': 'different', 'title': '旧暗示', 'version': 1, 'accepted_stage': 'planted', 'planted_chapter': 3,
         'schedule': {'payoff_chapter': 7, 'payoff_event': 'check'}},
    ], 'current_chapter': 5, 'current_events': ['check']}
    guard = build_continuity_ledger('action_design', products, [], context)['foreshadow_reminder']
    assert guard['lifecycle_counts'] == {'unverified': 1, 'planted': 2, 'hinted': 0, 'paid_off': 0}
    assert [row['promise'] for row in guard['due_this_scene']] == ['confirmed']
    assert guard['still_open'] == ['different']
    assert guard['unverified'] == ['new']
    assert 'foreshadow_reminder' not in (build_continuity_ledger('writing', products, [], context) or {})


def test_private_payoff_is_not_given_to_prose_but_approved_scene_check_is():
    from nw.materials.evidence import writer_checks
    from test_material_stage_procedures import material, members, output

    procedure = output('promise_process')
    procedure['observable'] = 'secret-future-payoff'
    procedure['entries'][0]['observable'] = 'reader-visible-clue'
    checks = writer_checks({'materials': [material('promise_process')], 'bindings': {},
        'process_bindings': {'source-id': procedure}, 'material_key': 'scene', 'scene_card_id': 'scene-1',
        'chapter_index': 1, 'scene_members': members()})
    project = {'brief': None, 'holder': 'pov', 'facts': [], 'settings': [
        {'card_id': 'sealed-door', 'kind': 'promise', 'body': {'title': 'Identity of the traitor',
         'setup': 'author-side planting', 'payoff': 'secret-future-payoff', 'visibility': 'public'}},
    ], 'material_checks': checks}
    scene = {'card_id': 'scene-1', 'body': {'pov': 'pov', 'title': '查证'}}
    result = {item.source: item.text for item in StoryProvider().build(project, scene).items}
    assert 'card:sealed-door' not in result
    assert 'reader-visible-clue' in str(result)
    assert 'secret-future-payoff' not in str(result)


def test_legacy_scene_links_pin_promise_but_write_only_approved_scene_disclosure(tmp_path):
    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        store.init_project('隔离旧场景写作')
        person = _approved(store, 'character', 'pov', {'name': '沈砚', 'role': '主角', 'want': '调查',
                                                      'visibility': 'public'})
        promise = _approved(store, 'promise', 'thread', {'title': 'author-side-title', 'setup': 'author-side-setup',
                            'payoff': 'author-side-payoff', 'visibility': 'public'})
        scene = _approved(store, 'scene', 'watch', {'title': '查证', 'goal': '展示物证', 'pov': 'pov',
                          'allowed_disclosure': 'reader-visible-clue', 'story_time': '1'})
        refs = [{k: record[k] for k in ('card_id', 'version')} for record in (scene, promise)]
        link_cards(store, *(CardRef(**ref) for ref in refs), 'depends_on')
        chapter = store.add_chapter(1, '旧章')
        target = store.add_scene(chapter.id, 1, canonical({'story': {'scene_ref': refs[0], 'story_order': 1}}))
        adopt_story(store, baseline(card_refs=[person, promise, scene]), {})
        work = build_story_context(store, target.id, scene_scope(store, target.id), 45000)
        text = str(work.package)
        assert refs[1] in work.card_refs
        assert 'reader-visible-clue' in text
        assert 'author-side-payoff' not in text
