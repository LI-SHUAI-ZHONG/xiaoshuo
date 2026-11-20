"""Keep original-source uses attached to the project products adopted by each scene."""
from collections import defaultdict

from nw.materials.phase_lifecycle import CANDIDATE_SELECTION, selected_scene_refs
from nw.materials.semantic_application import pointer_tokens
from nw.materials.semantic_checks import current_scene_outputs


POLICY = 'scene-source-binding-v1'
SCENE_FIELDS = {
    'scene_design': {'members', 'chapters', 'events', 'selected_events', 'selected_actions'},
    'state_transition': {'patches', 'transitions'},
    'anchor_design': {'beats', 'selected_propagations'},
    'expression_design': {'guidance'},
    'bind_scope': {'method_guidance'},
}


def _applied_outputs(value: dict) -> dict[str, set[str]]:
    return {
        row['source_id']: {ref for clause in row['clauses'] if clause['applicability'] == 'applies'
                           for ref in clause['output_refs']}
        for row in value.get('_criteria', [])
    }


def validate_candidate_sources(stage: str, value: dict) -> None:
    if stage not in CANDIDATE_SELECTION:
        return
    prefix = CANDIDATE_SELECTION[stage][3]
    sources_by_output = defaultdict(set)
    uses = {use['source_id']: set(use['output_refs']) for use in value['_uses']}
    for ident, refs in uses.items():
        for ref in refs:
            sources_by_output[ref].add(ident)
    refs = [f'{prefix}:{candidate["id"]}' for candidate in value['candidates']]
    for ref, candidate in zip(refs, value['candidates'], strict=True):
        if set(candidate['source_ids']) != sources_by_output[ref]:
            raise ValueError(f'MATERIAL_STAGE: candidate source IDs differ from actual uses for {ref}')

    for ident, paths in _applied_outputs(value).items():
        outputs = set()
        for path in paths:
            field, *tokens = pointer_tokens(path)
            if field != 'candidates':
                raise ValueError('MATERIAL_STAGE: applied clause must reference an actual candidate: ' + ident)
            if tokens:
                outputs.add(refs[int(tokens[0])])
            else:
                outputs.update(refs)
        if outputs != uses[ident]:
            raise ValueError('MATERIAL_STAGE: source clauses and use record reference different candidates: ' + ident)


def scene_source_placements(products: dict, binding: dict | None = None) -> tuple[dict[str, set[str]], set[str]]:
    """Resolve required scenes and identify sources with an additional book/scene-independent use."""
    scenes = {row['key'] for row in products['scene_design']['products']['members']}
    choices = selected_scene_refs(products)
    records = products if binding is None else {**products, 'bind_scope': {'products': binding}}
    required = defaultdict(set)
    flexible = set()
    for stage, record in records.items():
        value = record['products']
        applications = _applied_outputs(value)
        for use in value.get('_uses', []):
            ident = use['source_id']
            if stage in choices:
                for ref in use['output_refs']:
                    for scene in choices[stage].get(ref, ()):
                        required[ident].add(scene)
                continue
            direct = {target for prefix, _, target in (ref.partition(':') for ref in use['output_refs'])
                      if target in scenes and (prefix in ('scene', 'guidance') or
                                               prefix == 'member' and stage == 'scene_design')}
            scoped_paths = [path for path in sorted(applications.get(ident, ()))
                            if pointer_tokens(path)[0] in SCENE_FIELDS.get(stage, ())]
            # Reuse the writer/reviewer projection for paths into individual scene rows.
            scoped = {scene for scene in scenes
                      if scoped_paths and current_scene_outputs(stage, value, scoped_paths, records, scene, {})}
            placed = direct | scoped
            if placed:
                required[ident].update(placed)
            else:
                flexible.add(ident)
    return dict(required), flexible


def validate_scene_sources(binding: dict, products: dict) -> None:
    required, flexible = scene_source_placements(products, binding)
    placed = defaultdict(set)
    for guide in binding['method_guidance']:
        for ident in guide['source_ids']:
            placed[ident].add(guide['scene'])
    for ident, scenes in sorted(required.items()):
        if missing := sorted(scenes - placed[ident]):
            raise ValueError(f'MATERIAL_STAGE: method lost its actual scene placement: {ident} → {", ".join(missing)}')
        if ident not in flexible and (extra := sorted(placed[ident] - scenes)):
            raise ValueError(f'MATERIAL_STAGE: method was assigned to the wrong scene: {ident} → {", ".join(extra)}')
