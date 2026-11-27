"""Freeze static prerequisites before admitting a same-stage derived method."""
from copy import deepcopy

from nw.materials.phase_routes import phase_order, product_ref
from nw.task_models import content_sha256


POLICY = 'network-static-followup-v1'
BASIS_STAGE = 'static_relations_basis'
STAGE = 'static_relations'
DELTA_FIELDS = {'requirements', '_uses', '_excluded', '_criteria'}
RELATION_FIELDS = {'source', 'target', 'relation', 'condition'}


def basis_inputs(products: dict, basis: dict) -> dict:
    from nw.materials.semantic_application import require

    require(basis.get('stage') == STAGE and BASIS_STAGE not in products, 'invalid static relation basis stage')
    product_ref(basis)
    return {**products, BASIS_STAGE: {**basis, 'stage': BASIS_STAGE}}


def _source_rows(rows: list[dict], permitted: set[str]) -> dict[str, dict]:
    from nw.materials.semantic_application import require

    result = {}
    for row in rows:
        require(isinstance(row, dict) and isinstance(row.get('source_id'), str)
                and row['source_id'] in permitted - result.keys(), 'static follow-up has an unoffered or duplicate source')
        result[row['source_id']] = row
    return result


def _related_requirements(use: dict, requirements: dict[str, tuple[int, dict]], ident: str) -> set[str]:
    from nw.materials.semantic_application import require

    refs = use.get('output_refs')
    require(isinstance(refs, list) and bool(refs) and all(isinstance(ref, str) for ref in refs)
            and len(set(refs)) == len(refs), 'static follow-up use needs exact new requirement references')
    claimed = set(refs)
    owned = {ref for ref, (_, row) in requirements.items() if row['source_id'] == ident}
    require(claimed == owned, 'static follow-up use must claim only its own actual requirements')
    return claimed


def _validate_applications(criterion: dict, own: set[str], requirements: dict[str, tuple[int, dict]],
                           relations: dict[str, dict]) -> None:
    from nw.materials.semantic_application import require
    from nw.materials.semantic_products import _cites_relation

    clauses = criterion.get('clauses')
    require(isinstance(clauses, list) and all(isinstance(clause, dict) for clause in clauses),
            'static follow-up requires per-clause applications')
    covered = set()
    for clause in clauses:
        inputs = clause.get('input_refs')
        require(isinstance(inputs, list) and all(isinstance(ref, str) and ref.startswith(
            (f'input:{BASIS_STAGE}:', 'brief:')) for ref in inputs),
            'static follow-up clause may cite only the delivered brief and frozen relation')
        if clause.get('applicability') != 'applies':
            continue
        outputs = clause.get('output_refs')
        require(isinstance(outputs, list) and bool(outputs) and all(isinstance(ref, str) for ref in outputs),
                'static follow-up clause needs frozen relation inputs and exact requirement outputs')
        basis_refs = {ref for ref in inputs if ref.startswith(f'input:{BASIS_STAGE}:')}
        for output in outputs:
            targets = [ref for ref in own if output == f'/requirements/{requirements[ref][0]}'
                       or output.startswith(f'/requirements/{requirements[ref][0]}/')]
            require(len(targets) == 1, 'static follow-up clause must cite its own new requirement row')
            [target] = targets
            row = requirements[target][1]
            members = {ref.removeprefix('member:') for ref in row['project_refs'] if ref.startswith('member:')}
            paths = {ref for ref, relation in relations.items() if {relation['source'], relation['target']} == members}
            require(bool(basis_refs) and all(any(_cites_relation(ref, {citation}) for ref in paths)
                                             for citation in basis_refs),
                    'static follow-up clause must cite the frozen relation of its requirement endpoints')
            require(clause.get('consumer') == row['target_stage'],
                    'static follow-up clause consumer must match its actual next-stage requirement')
            covered.add(target)
    require(covered == own, 'static follow-up requirements need an applied clause for each exact row')


def merge_followup(basis: dict, delta: dict, sources: list[dict], products: dict, context: dict) -> dict:
    """Append only the separately validated work. Retain the original relation products verbatim."""
    from nw.materials.network_workflow import DYNAMIC_PROFILES, POLICY as NETWORK_POLICY
    from nw.materials.semantic_application import concrete, require
    from nw.materials.semantic_products import dynamic_rejection, original, _network_relation_inputs

    require(context.get('same_stage_network_policy') == POLICY and context.get('network_prerequisite_policy') == NETWORK_POLICY,
            'static follow-up policy is not active')
    snapshot = basis_inputs(products, basis)
    require(isinstance(delta, dict) and set(delta) == DELTA_FIELDS and all(isinstance(rows, list) for rows in delta.values()),
            'static follow-up must only append requirements and source decisions')
    by_id = {source['source']['id']: source for source in sources}
    ids = set(by_id)
    require(bool(ids) and len(by_id) == len(sources) and not ids & set(basis['source_ids']),
            'static follow-up must have distinct newly offered sources')
    uses = _source_rows(delta['_uses'], ids)
    exclusions = _source_rows(delta['_excluded'], ids - uses.keys())
    criteria = _source_rows(delta['_criteria'], set(uses))
    require(uses.keys() | exclusions.keys() == ids and criteria.keys() == uses.keys(),
            'static follow-up needs one decision per source and criteria for adopted sources')

    former = basis['products']['requirements']
    seen = {row['id'] for row in former}
    order = phase_order(context.get('scope', 'chapter'), planning_hierarchy=context.get('planning_hierarchy', False))
    later = set(order[order.index(STAGE) + 1:])
    requirements = {}
    for index, row in enumerate(delta['requirements'], start=len(former)):
        require(isinstance(row, dict) and set(row) == {'id', 'source_id', 'target_stage', 'constraint', 'project_refs'}
                and isinstance(row['id'], str) and row['id'].strip() and row['id'] not in seen
                and isinstance(row['source_id'], str) and row['source_id'] in uses
                and isinstance(row['target_stage'], str) and row['target_stage'] in later and concrete(row['constraint'])
                and isinstance(row['project_refs'], list) and all(isinstance(ref, str) for ref in row['project_refs']),
                'static follow-up needs a new concrete requirement for a later stage in scope')
        seen.add(row['id'])
        requirements['requirement:' + row['id']] = index, row

    for ident, source in by_id.items():
        raw = original(source)
        require(source['source']['profile'] in DYNAMIC_PROFILES and isinstance(raw, dict)
                and raw.get('generated_from_static') is True,
                'static follow-up only accepts rules derived from original static edges')
        reason = dynamic_rejection(source, snapshot, context)
        require(not reason, source['source']['key'] + '：' + reason)
        relations = {ref: relation for ref, relation in _network_relation_inputs(source, raw, snapshot, context).items()
                     if ref.startswith(f'input:{BASIS_STAGE}:')}
        require(bool(relations), 'static follow-up needs an independently frozen corresponding project relation')
        if ident in uses:
            own = _related_requirements(uses[ident], requirements, ident)
            _validate_applications(criteria[ident], own, requirements, relations)

    merged = deepcopy(basis['products'])
    for key, rows in delta.items():
        if rows or key in merged:
            merged[key] = [*merged.get(key, []), *deepcopy(rows)]
    return merged


def verify_followup(record: dict, products: dict, sources: dict, context: dict, calls: list[dict]) -> dict:
    """Rebuild a stored second pass and validate its independently saved first pass."""
    from nw.materials.network_workflow import DYNAMIC_PROFILES
    from nw.materials.phase_contract import validate_phase
    from nw.materials.semantic_application import require
    from nw.materials.semantic_products import original
    from nw.production_methods import runtime as project_methods

    basis = record.get('static_relations_basis')
    followup = record.get('static_relations_followup')
    if 'static_relations_basis' not in record and 'static_relations_followup' not in record:
        if record['stage'] == STAGE and context.get('same_stage_network_policy') == POLICY:
            for ident in record['source_ids']:
                source = sources[ident]
                if source['source']['profile'] in DYNAMIC_PROFILES:
                    raw = original(source)
                    require(not isinstance(raw, dict) or not raw.get('generated_from_static'),
                            'same-stage derived source requires its frozen static follow-up, even if excluded')
        return products
    require(record['stage'] == STAGE and context.get('same_stage_network_policy') == POLICY
            and isinstance(basis, dict) and isinstance(followup, dict)
            and set(followup) == {'products', 'sha256', 'source_ids', 'task_id', 'manifest_id'}
            and isinstance(basis.get('source_ids'), list) and isinstance(followup['source_ids'], list)
            and followup['sha256'] == content_sha256(followup['products']), 'invalid frozen static follow-up record')
    snapshot = basis_inputs(products, basis)
    require(record['inputs'] == basis['inputs'] and record['task_id'] == followup['task_id']
            and basis['task_id'] != followup['task_id'] and record['source_ids'] == basis['source_ids'] + followup['source_ids'],
            'static follow-up changed its independent inputs, calls or source identities')
    basis_calls = [row for row in calls if row.get('task_id') == basis['task_id']]
    followup_calls = [row for row in calls if row.get('task_id') == followup['task_id']]
    require(len(basis_calls) == len(followup_calls) == 1 and followup_calls[0].get('manifest_id') == followup['manifest_id']
            and calls.index(basis_calls[0]) < calls.index(followup_calls[0]),
            'static follow-up requires its two original call records in order')
    kept = [sources[ident] for ident in basis['source_ids']]
    if context.get('binding_policy'):
        selection = basis.get('source_selection', {})
        used = {row['source_id'] for row in basis['products']['_uses']}
        require(selection.get('before_stage') == STAGE and selection.get('upstream') == basis['inputs']
                and selection.get('offered') == [row['source'] for row in kept]
                and selection.get('selected') == [row['source'] for row in kept if row['source']['id'] in used]
                and basis.get('prepared_static_sources') == record.get('prepared_static_sources'),
                'static follow-up needs the unchanged first-pass source selection')
    clean, _ = project_methods.split({'stage': STAGE, 'products': basis['products']})
    validate_phase(clean, STAGE, products, kept, {**context, 'allowed_input_stages': [row['stage'] for row in basis['inputs']]})
    merged = merge_followup(basis, followup['products'], [sources[ident] for ident in followup['source_ids']], products, context)
    require(merged == record['products'], 'saved static follow-up cannot rewrite its frozen relation or first-pass decisions')
    return snapshot
