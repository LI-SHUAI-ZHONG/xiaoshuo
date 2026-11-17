"""Conditional event, action and propagation designs never assert story facts."""
from nw.materials.template_support import (capabilities, content, events, identified, members,
    product, references, require, rows, source_ids, strings, text, waiting)
from nw.task_models import canonical
import re

PROPAGATION_GATES={'require_root_confirmation':True,'require_external_action_selection':True,
                   'require_continuity_validation':True}


def validate_nodes(value: dict, products: dict, context: dict) -> None:
    fields = {'id', 'actors', 'goal', 'setting', 'obstacle', 'completion_condition', 'status'}
    people = members(products, context, {'character'})
    for row in identified(value, 'event_nodes', fields):
        require(references(row['actors'], people) and row['status'] == 'planned'
                and all(content(row[key]) for key in ('goal', 'setting', 'obstacle', 'completion_condition')),
                'event nodes need actual people, design content and planned status')


def validate_events(value: dict, products: dict, sources: list[dict], context: dict) -> None:
    fields = {'id', 'source_ids', 'predecessor', 'event', 'actors', 'completion_gate', 'status'}
    nodes = {row['id']: row for row in product(products, 'plot_design').get('event_nodes', [])}
    people = members(products, context, {'character'})
    for row in identified(value, 'candidates', fields, nodes):
        require(references(row['source_ids'], source_ids(sources), nonempty=False)
                and text(row['predecessor']) and row['predecessor'] in nodes
                and references(row['actors'], people) and content(row['event'])
                and row['status'] == 'conditional_candidate',
                'successor events need a real predecessor and conditional candidate status')
        require(row['completion_gate'] == nodes[row['predecessor']]['completion_condition'],
                'successor completion gate differs from the actual predecessor condition')


def validate_actions(value: dict, products: dict, sources: list[dict], context: dict) -> None:
    fields = {'id', 'source_ids', 'event', 'actor', 'action', 'steps', 'requires', 'cost', 'limits', 'status'}
    people = members(products, context, {'character'})
    available = capabilities(products); actual_events = events(products)
    for row in identified(value, 'candidates', fields):
        require(references(row['source_ids'], source_ids(sources), nonempty=False)
                and text(row['event']) and row['event'] in actual_events
                and text(row['actor']) and row['actor'] in people
                and row['actor'] in actual_events[row['event']]['actors']
                and all(content(row[key]) for key in ('action', 'cost'))
                and strings(row['limits']) and row['status'] == 'candidate',
                'action needs an actual event actor, designed action and candidate status')
        capability = available.get(row['actor'], {})
        require(capability.get('can_act') is True
                and references(row['requires'], capability.get('abilities', [])),
                'action actor lacks its declared minimum capabilities')
        steps = rows(row, 'steps', {'object', 'action', 'obstacle', 'response', 'result'})
        require(bool(steps) and all(all(content(item) for item in step.values()) for step in steps),
                'action steps must be actual object, action, obstacle, response and result designs')
    waiting(value, sources)


def _confirmed_root(row: dict, products: dict, context: dict) -> None:
    if row['root_kind'] == 'planned_change':
        roots = [root for root in product(products, 'state_transition').get('transitions', [])
                 if root['event'] == row['root_id'] and root['entity'] == row['source_entity']]
        require(len(roots) == 1, 'propagation has no unique planned state-change root for its source entity')
        root = roots[0]
        require(isinstance(root.get('after_state'), dict) and bool(root['after_state'])
                and root['after_state'] != root.get('before_state'), 'propagation root has no actual planned change')
        require(row['scene'] is None or row['scene'] == root['scene'],
                'propagation scene differs from its planned root scene')
    else:
        require(row['root_kind'] == 'accepted_fact' and text(row['root_id'])
                and row['root_id'].startswith('fact:'), 'unknown propagation root kind or fact reference')
        raw_index = row['root_id'][5:]
        require(raw_index.isdigit(), 'accepted fact root needs a nonnegative context index')
        index = int(raw_index); facts = context.get('accepted_state', [])
        require(index < len(facts), 'accepted fact root does not exist')
        fact = facts[index]
        require(fact.get('claim') == 'fact' and fact.get('entity_id') == row['source_entity']
                and isinstance(fact.get('evidence'), (list, tuple)) and bool(fact['evidence'])
                and all(isinstance(span, dict) and bool(span) for span in fact['evidence']),
                'propagation needs an accepted fact with evidence for the corresponding entity')
        matches=[op for op in context.get('accepted_changes',[])
            if op.get('claim')=='fact' and op.get('holder')=='WORLD' and fact.get('holder')=='WORLD'
            and op.get('entity_id')==fact['entity_id'] and op.get('predicate')==fact.get('predicate')
            and op.get('expected_old') is not None and canonical(op['expected_old'])!=canonical(op.get('new_value'))
            and canonical(op.get('new_value'))==canonical(fact.get('value'))
            and op.get('story_order')==fact.get('story_order')
            and canonical(op.get('evidence'))==canonical(fact['evidence'])]
        require(bool(matches),'accepted propagation root needs an actual accepted change, not merely a static fact')


def _activation_gate(condition: str) -> bool:
    value = condition.casefold()
    for clause in re.split(r'[；;。\n]',value):
        negative=any(token in clause for token in ('未经确认','未被确认','未确认','没有作出','没有选择',
            '不需确认','无需','无须','not confirmed','not verified','without confirmation',
            'without an external','without external','no external'))
        negative=negative or bool(re.search(r'(?:not|never)\s+(?:been\s+)?(?:confirm|verif|select|chosen)',clause))
        safe=any(token in clause for token in ('等待','停止','不传播','不能','不应','不得','禁止','不允许',
                                               'wait','do not propagat','must not propagat'))
        if negative and not safe:return False
    return (any(word in value for word in ('确认', '证实', 'confirm', 'verif'))
            and any(word in value for word in ('选择', '决定', '选定', 'choos', 'select', 'choice', 'decid'))
            and any(word in value for word in ('当', '若', '如果', '仅在', '只有', '待', '后',
                                               'if ', 'when ', 'after ', 'once ', 'upon ')))


def validate_propagations(value: dict, products: dict, sources: list[dict], context: dict) -> None:
    fields = {'id', 'source_ids', 'root_kind', 'root_id', 'source_entity', 'target_entity',
              'external_action', 'proposed_effect', 'continuity', 'scene', 'status', 'activation_condition','gates'}
    entities = members(products, context, {'character', 'world'})
    designs = members(products, context, {'promise', 'plot'})
    people = members(products, context, {'character'})
    scenes = {row['key'] for row in product(products, 'scene_design').get('members', [])}
    available = capabilities(products)
    for row in identified(value, 'candidates', fields):
        from nw.materials.semantic_products import original,adopted_relation
        own=[s for s in sources if s['source']['id'] in row.get('source_ids',[])]
        source_bound=any(isinstance(original(s),dict) and original(s).get('generated_from_static')
            and any(r['source']==row.get('source_entity') and r['target']==row.get('target_entity')
                    for r in adopted_relation(s,products,context)) for s in own)
        require(references(row['source_ids'], source_ids(sources), nonempty=False)
                and text(row['source_entity']) and row['source_entity'] in people
                and text(row['target_entity']) and row['target_entity'] in (entities|designs if source_bound else entities)
                and (row['scene'] is None or text(row['scene']) and row['scene'] in scenes)
                and row['status'] == 'conditional_candidate'
                and all(content(row[key]) for key in ('external_action', 'continuity', 'activation_condition'))
                and isinstance(row['proposed_effect'], dict) and bool(row['proposed_effect']),
                'propagation must preserve actual entities, root and explicitly conditional candidate status')
        require(available.get(row['source_entity'], {}).get('can_act') is True,
                'propagation source has no actual capability to act')
        require(_activation_gate(row['activation_condition']),
                'propagation must condition activation on root confirmation and an external choice')
        require(isinstance(row['gates'],dict) and row['gates']==PROPAGATION_GATES
                and all(v is True for v in row['gates'].values()),
                'propagation must preserve mandatory structured activation gates')
        _confirmed_root(row, products, context)
    waiting(value, sources)


def validate_scene_selection(value: dict, products: dict) -> None:
    scenes = {row['key']: row['body'] for row in value['members']}
    actual_events = events(products)
    actions = {row['id']: row for row in product(products, 'action_design').get('candidates', [])}
    selected_events = {}
    for row in rows(value, 'selected_events', {'scene', 'event'}):
        require(text(row['scene']) and row['scene'] in scenes and row['scene'] not in selected_events
                and text(row['event']) and row['event'] in actual_events,
                'scene must select one actual event node or conditional event candidate')
        selected_events[row['scene']] = row['event']
    selected_actions = set()
    for row in rows(value, 'selected_actions', {'scene', 'action'}):
        require(text(row['scene']) and row['scene'] in scenes and row['scene'] not in selected_actions
                and text(row['action']) and row['action'] in actions,
                'scene must select one actual action candidate')
        scene = scenes[row['scene']]; action = actions[row['action']]
        require(action['actor'] in {scene['pov'], *scene['characters']}
                and action['event'] == selected_events.get(row['scene']),
                'selected action actor or event does not belong to the actual scene selection')
        selected_actions.add(row['scene'])
    require(set(selected_events) == selected_actions == set(scenes), 'every actual scene needs one event and one action selection')


def validate_propagation_selection(value: dict, products: dict) -> None:
    scenes = {row['key'] for row in product(products, 'scene_design').get('members', [])}
    propagations = {row['id']: row for row in product(products, 'state_propagation').get('candidates', [])}
    seen = set()
    for row in rows(value, 'selected_propagations', {'scene', 'propagation'}):
        require(text(row['scene']) and row['scene'] in scenes and text(row['propagation'])
                and row['propagation'] in propagations and (row['scene'], row['propagation']) not in seen,
                'anchor selection requires an actual scene and propagation candidate')
        require(propagations[row['propagation']]['scene'] in (None, row['scene']),
                'selected propagation belongs to another actual scene')
        seen.add((row['scene'], row['propagation']))
