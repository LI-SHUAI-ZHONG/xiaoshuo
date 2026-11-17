"""Scene budget evidence comes from actual dynamic candidate design artifacts."""
from copy import deepcopy


RULE_CLASSES = {
    'type_dynamic': {'path': 'types.txt', 'file_sha256': 'a' * 64},
    'original_dynamic': {'path': 'dynamic.txt', 'file_sha256': 'b' * 64},
}
SOURCE = {'filter_id': 'TDF_001', 'source_ref': {'id': 'tdf'},
          'limits': {'max_type_dynamic_rules': 5, 'max_original_dynamic_rules': 5},
          'sources': RULE_CLASSES}


def _ref(family: str, ident: int) -> dict:
    native = f'TDR_{ident:03}' if family=='type_dynamic' else f'C{ident:05}'
    return {'id': f'{family}-{ident}', 'key': native, 'sha256': f'{ident:064x}', **RULE_CLASSES[family]}


def test_per_scene_rule_budgets_count_source_ids_from_concrete_designs() -> None:
    from nw.materials.dynamic_screening import screening_report

    types = [_ref('type_dynamic', i) for i in range(1, 8)]
    originals = [_ref('original_dynamic', i) for i in range(1, 6)]
    staged = {
        'scene_design': {'products': {
            'members': [{'key': 'A'}, {'key': 'B'}],
            'selected_events': [{'scene': 'A', 'event': 'e1'}, {'scene': 'B', 'event': 'e2'}],
            'selected_actions': [{'scene': 'A', 'action': 'a1'}, {'scene': 'B', 'action': 'a2'}],
        }},
        'action_design': {
            'products': {'candidates': [
                {'id': 'a1', 'event': 'e1', 'source_ids': [types[0]['id']]},
                {'id': 'a2', 'event': 'e2', 'source_ids': [types[5]['id']]},
            ], '_uses': [{'source_id': source['id']} for source in (types[0], types[5])]},
            'source_selection': {'selected': [types[0], types[5]]},
        },
        'state_propagation': {
            'products': {'candidates': [
                {'id': 'p1', 'scene': 'A', 'root_kind': 'planned_change', 'root_id': 'x',
                 'source_entity': 'yan', 'source_ids': [source['id'] for source in [*types[:5], *originals]]},
                {'id': 'p2', 'scene': None, 'root_kind': 'accepted_fact', 'root_id': 'fact:0',
                 'source_entity': 'yan', 'source_ids': [types[6]['id']]},
            ], '_uses': [{'source_id': source['id']} for source in [*types[:5], types[6], *originals]]},
            'source_selection': {'selected': [*types[:5], types[6], *originals]},
        },
    }
    report = screening_report(staged, SOURCE)
    assert report['scenes']['A']['counts'] == {'type_dynamic': 5, 'original_dynamic': 5}
    assert report['scenes']['B']['counts'] == {'type_dynamic': 1, 'original_dynamic': 0}
    assert report['unassigned'][0]['candidate'] == 'p2'
    assert report['scenes']['A']['rules'][0]['source_ref']['file_sha256']
    assert {r['source_type'] for r in report['scenes']['A']['rules']} == set(RULE_CLASSES)
    assert not report['violations']

    chosen = {'products': {'selected_propagations': [{'scene': 'A', 'propagation': 'p2'}]}}
    staged_with_choice = {**deepcopy(staged), 'anchor_design': chosen}
    over = screening_report(staged_with_choice, SOURCE)
    assert over['scenes']['A']['counts']['type_dynamic'] == 6
    assert over['violations'] == [{'scene': 'A', 'source_type': 'type_dynamic', 'count': 6, 'limit': 5}]
    assert not over['unassigned']


def test_actual_output_references_cannot_hide_rules_from_the_scene_limits() -> None:
    from nw.materials.dynamic_screening import screening_report

    rules = [_ref('type_dynamic', i) for i in range(1, 7)]
    stages = {
        'scene_design': {
            'products': {
                'members': [{'key': 'A'}], 'selected_events': [{'scene': 'A', 'event': 'event'}],
                'selected_actions': [{'scene': 'A', 'action': 'action'}],
                '_uses': [{'source_id': rules[0]['id'], 'output_refs': ['member:A']}],
            },
            'source_selection': {'selected': rules[:1]},
        },
        'event_design': {
            'products': {'candidates': [{'id': 'event', 'source_ids': []}],
                         '_uses': [{'source_id': rules[1]['id'], 'output_refs': ['event_candidate:event']}]},
            'source_selection': {'selected': rules[1:2]},
        },
        'action_design': {
            'products': {'candidates': [{'id': 'action', 'event': 'event', 'source_ids': [rules[2]['id']]}],
                         '_uses': [{'source_id': rules[2]['id'], 'output_refs': ['action:action']}]},
            'source_selection': {'selected': rules[2:3]},
        },
        'state_propagation': {
            'products': {'candidates': [{'id': 'effect', 'scene': 'A', 'source_ids': []}],
                         '_uses': [{'source_id': r['id'], 'output_refs': ['propagation:effect']} for r in rules[3:]]},
            'source_selection': {'selected': rules[3:]},
        },
    }
    report = screening_report(stages, SOURCE)
    assert report['violations'] == [{'scene': 'A', 'source_type': 'type_dynamic', 'count': 6, 'limit': 5}]
    assert {r['source_ref']['id'] for r in report['scenes']['A']['rules']} == {rule['id'] for rule in rules}


def test_shared_event_does_not_assign_a_different_scenes_action() -> None:
    from nw.materials.dynamic_screening import screening_report

    rules = [_ref('type_dynamic', i) for i in (1, 2, 3)]
    stages = {
        'scene_design': {'products': {
            'members': [{'key': 'A'}, {'key': 'B'}],
            'selected_events': [{'scene': scene, 'event': 'shared'} for scene in ('A', 'B')],
            'selected_actions': [{'scene': 'A', 'action': 'one'}, {'scene': 'B', 'action': 'two'}],
        }},
        'action_design': {
            'products': {'candidates': [{'id': key, 'event': 'shared', 'source_ids': [rule['id']]}
                                        for key, rule in zip(('one', 'two', 'unassigned'), rules)]},
            'source_selection': {'selected': rules},
        },
    }
    report = screening_report(stages, SOURCE)
    assert {scene: data['counts']['type_dynamic'] for scene, data in report['scenes'].items()} == {'A': 1, 'B': 1}
    assert [row['candidate'] for row in report['unassigned']] == ['unassigned']


def test_applied_clause_output_is_counted_at_its_actual_scene() -> None:
    from nw.materials.dynamic_screening import screening_report

    rules = [_ref('original_dynamic', i) for i in range(1, 7)]
    alternatives = [f'B{i}' for i in range(1, 7)]
    stages = {
        'scene_design': {'products': {'members': [{'key': scene} for scene in ['A', *alternatives]]}},
        'state_transition': {
            'products': {
                'transitions': [{'scene': scene, 'after_state': {'hand': '受伤'}} for scene in ['A', *alternatives]],
                '_uses': [{'source_id': rule['id'], 'output_refs': [f'scene:{scene}']}
                          for rule, scene in zip(rules, alternatives)],
                '_criteria': [{'source_id': rule['id'], 'clauses': [
                    {'applicability': 'applies', 'output_refs': ['/transitions/0/after_state']}]}
                              for rule in rules],
            },
            'source_selection': {'selected': rules},
        },
    }
    report = screening_report(stages, SOURCE)
    assert report['violations'] == [{'scene': 'A', 'source_type': 'original_dynamic', 'count': 6, 'limit': 5}]
    assert report['scenes']['A']['rules'][0]['placements'][0]['product'] == '/transitions/0/after_state'
