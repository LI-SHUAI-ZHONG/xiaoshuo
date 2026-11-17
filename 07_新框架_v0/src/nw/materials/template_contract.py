"""Validate project instances of distinct source templates without activating them."""
from nw.materials.template_candidates import (validate_actions, validate_events, validate_nodes,
    validate_propagation_selection, validate_propagations, validate_scene_selection)
from nw.materials.template_support import (content, identified, members, product, references,
    require, rows, source_ids, strings, text)

_STAGES = ('type_selection', 'type_adaptation', 'world_design', 'character_design',
           'static_relations', 'plot_design', 'event_design', 'action_design', 'scene_design',
           'state_transition', 'state_propagation', 'anchor_design', 'expression_design', 'bind_scope')
_REFS = {'type_selection': (('concepts', 'concept'),),
         'type_adaptation': (('adaptations', 'adaptation'), ('focuses', 'focus')),
         'static_relations': (('requirements', 'requirement'),),
         'plot_design': (('event_nodes', 'event_node'),),
         'event_design': (('candidates', 'event_candidate'),),
         'action_design': (('candidates', 'action'),),
         'state_propagation': (('candidates', 'propagation'),)}
_TEMPLATES = {1: ('state_propagation', 'candidates', 'propagation'),
              2: ('type_adaptation', 'focuses', 'focus'),
              3: ('state_transition', 'transitions', 'scene'),
              4: ('event_design', 'candidates', 'event_candidate'),
              5: ('action_design', 'candidates', 'action')}


def extra_refs(stage: str, value: dict) -> set[str]:
    """Name actual additional outputs; waiting records never represent application."""
    return {f'{prefix}:{row["id"]}' for key, prefix in _REFS.get(stage, ())
            for row in value.get(key, []) if isinstance(row, dict) and text(row.get('id'))}


def _selection(value: dict) -> None:
    selected = identified(value, 'selection', {'id', 'label', 'basis'})
    for row in selected:
        require(content(row['label']) and content(row['basis']), 'selected type needs its actual project label and basis')
    choices = {row['id'] for row in selected}
    for row in identified(value, 'concepts', {'id', 'label', 'type_refs', 'activation_basis'}):
        require(content(row['label']) and content(row['activation_basis']) and references(row['type_refs'], choices),
                'activated project concept must reference actually selected types and its activation basis')


def _parameter(value: object) -> bool:
    if isinstance(value, dict):
        return bool(value) and all(text(key) and _parameter(item) for key, item in value.items())
    if isinstance(value, list):
        return bool(value) and all(_parameter(item) for item in value)
    return content(value) if isinstance(value, str) else value is not None


def _adaptation(value: dict, products: dict) -> None:
    selected = product(products, 'type_selection')
    choices = {row['id'] for row in selected.get('selection', [])}
    concepts = {row['id']: row for row in selected.get('concepts', [])}
    for row in identified(value, 'adaptations', {'id', 'type_refs', 'parameters', 'limits'}):
        require(references(row['type_refs'], choices) and isinstance(row['parameters'], dict)
                and _parameter(row['parameters']) and strings(row['limits']),
                'type adaptation needs selected types, actual parameters and explicit limits')
    for row in identified(value, 'focuses', {'id', 'concept', 'from_focus', 'to_focus', 'application'}):
        require(text(row['concept']) and row['concept'] in concepts
                and all(content(row[key]) for key in ('from_focus', 'to_focus', 'application'))
                and row['from_focus'].strip() != row['to_focus'].strip(),
                'focus needs an actually activated concept and a concrete change of attention')
        concept = concepts[row['concept']]
        require(content(concept.get('activation_basis')) and references(concept.get('type_refs'), choices),
                'focus concept has no real activated type basis')
    require(strings(value.get('boundaries')), 'type adaptation boundaries must be explicit')


def _capabilities(value: dict, products: dict, context: dict) -> None:
    people = members(products, context, {'character'}, value.get('members', [])); seen = set()
    for row in rows(value, 'capabilities', {'entity', 'can_act', 'abilities', 'basis', 'limits'}):
        require(text(row['entity']) and row['entity'] in people and row['entity'] not in seen
                and type(row['can_act']) is bool and strings(row['abilities'])
                and len(row['abilities']) == len(set(row['abilities']))
                and content(row['basis']) and strings(row['limits']),
                'capability needs an actual character and an explicit design or known-behavior basis')
        seen.add(row['entity'])


def _requirements(value: dict, products: dict, sources: list[dict], context: dict) -> None:
    entities = members(products, context, {'world', 'character', 'promise'})
    choices = {row['id'] for row in product(products, 'type_selection').get('selection', [])}
    allowed = {'brief'} | {'member:' + key for key in entities} | {'type:' + key for key in choices}
    later = set(_STAGES[_STAGES.index('static_relations') + 1:])
    for row in identified(value, 'requirements', {'id', 'source_id', 'target_stage', 'constraint', 'project_refs'}):
        require(text(row['source_id']) and row['source_id'] in source_ids(sources)
                and text(row['target_stage']) and row['target_stage'] in later and content(row['constraint'])
                and references(row['project_refs'], allowed),
                'method requirement needs a delivered method, real project refs and a later target stage')


def validate_extra(stage: str, value: dict, products: dict, sources: list[dict], context: dict) -> None:
    """Validate added products; the phase contract owns legacy fields and stage keys."""
    try:
        if stage == 'type_selection':
            _selection(value)
        elif stage == 'type_adaptation':
            _adaptation(value, products)
        elif stage == 'character_design':
            _capabilities(value, products, context)
        elif stage == 'static_relations':
            _requirements(value, products, sources, context)
        elif stage == 'plot_design':
            validate_nodes(value, products, context)
        elif stage == 'event_design':
            validate_events(value, products, sources, context)
        elif stage == 'action_design':
            validate_actions(value, products, sources, context)
        elif stage == 'scene_design':
            validate_scene_selection(value, products)
        elif stage == 'state_propagation':
            validate_propagations(value, products, sources, context)
        elif stage == 'anchor_design':
            validate_propagation_selection(value, products)
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        if str(exc).startswith(('MATERIAL_STAGE:', 'MATERIAL_WAITING_INPUTS:')):
            raise
        raise ValueError('MATERIAL_STAGE: ' + str(exc)) from exc


def _template_number(key: str) -> int | None:
    return next((number for number in _TEMPLATES if key.startswith(f'TDR_TEMPLATE_00{number}')), None)


def _actual_adaptations(stage: str, value: dict, products: dict) -> None:
    adapted = value if stage == 'type_adaptation' else product(products, 'type_adaptation')
    if not adapted.get('adaptations'):
        raise ValueError('MATERIAL_WAITING_INPUTS: type auxiliary method needs actual type adaptation products')
    _adaptation(adapted, products)


def validate_template_uses(stage: str, value: dict, products: dict, sources: list[dict], context: dict) -> None:
    """After basic _uses validation, require each template's own real project work."""
    try:
        allowed = {row['source']['id']: row['source'] for row in sources}
        for use in value.get('_uses', []):
            source = allowed[use['source_id']]
            if source.get('profile') in ('type_link', 'type_combination', 'type_expression'):
                _actual_adaptations(stage, value, products)
            number = _template_number(source['key'])
            if number is None:
                continue
            expected_stage, key, prefix = _TEMPLATES[number]
            require(stage == expected_stage, 'template source is applied outside its actual project-design stage')
            if any(row['source_id'] == use['source_id'] for row in value.get('waiting', [])):
                raise ValueError('MATERIAL_WAITING_INPUTS: template is waiting for actual prerequisites')
            if number == 3:
                require(bool(value.get('transitions')), 'entity-state template needs actual state transitions')
                actual={'scene:'+row['scene'] for row in value['transitions']}
                require(bool(use['output_refs']) and set(use['output_refs'])<=actual,
                        'entity-state use must cite only scenes with its actual state transitions')
                continue
            validate_extra(stage, value, products, sources, context)
            actual = {f'{prefix}:{row["id"]}' for row in value.get(key, [])
                      if number == 2 or use['source_id'] in row['source_ids']}
            require(bool(actual & set(use['output_refs'])),
                    'template use must cite its own corresponding actual project product')
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        if str(exc).startswith(('MATERIAL_STAGE:', 'MATERIAL_WAITING_INPUTS:')):
            raise
        raise ValueError('MATERIAL_STAGE: ' + str(exc)) from exc
