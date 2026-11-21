"""Carry immutable project outputs, including approved parent scope decisions."""
from copy import deepcopy

from nw.materials.phase_routes import product_ref
from nw.cards import _body
from nw.task_models import canonical,content_sha256


def outputs(records: list[dict],*,parent: dict | None=None,selected_direction: dict | None=None) -> list[dict]:
    result=[]
    for record in records:
        plan=record.get('production_methods')
        if not plan:continue
        methods={r['method']['id']:r['method'] for r in plan['selected']}
        for app in record['products'].get('_method_applications',[]):
            pin=methods[app['method_id']];body=pin['body'];definitions={o['key']:o for o in body['outputs']}
            for output in app['outputs']:
                value=deepcopy(output)
                if parent and selected_direction:
                    kept=[]
                    for placement in value['placements']:
                        path=placement['path']
                        if path[0]!='directions':kept.append(placement);continue
                        if len(path)==1:
                            kept.append({'path':['directions'],'value':[deepcopy(selected_direction)]});continue
                        direction=record['products']['directions'][path[1]]
                        if canonical(_body('plot',direction))==canonical(_body('plot',selected_direction)):kept.append(placement)
                    value['placements']=kept
                    if not kept:continue
                entry={'method':pin,'producer':product_ref(record),'output':value,'definition':definitions[output['key']],
                    'downstream':[d for d in body['downstream'] if d['output_key']==output['key']],
                    'acceptance':[a for a in body['acceptance'] if a['output_key']==output['key']]}
                if record['stage'] == 'world_design' and plan['target'].get('selection_mode') == 'ai' and entry['definition']['artifact_kind'] == 'world':
                    from nw.production_methods.world_selection import needs
                    target = plan['target']
                    indices = sorted({p['path'][1] for p in value['placements'] if p['path'][0] == 'members'})
                    entry['world_design_basis'] = {'upstream_refs': deepcopy(target['upstream_refs']),
                        'fields': deepcopy(app['design_basis']),
                        'members': [deepcopy(record['products']['members'][i]) for i in indices],
                        'needs': needs(target['demand'], target['type_ids'], target['adaptation_indices'])}
                if parent:entry['approved_parent']=deepcopy(parent)
                entry['id']='pm:'+content_sha256(entry)[:32];result.append(entry)
    return result


def retained_world(entry: dict, keys: set[str]) -> dict | None:
    """Keep the original receipt for intact rules and project a mixed output onto surviving cards."""
    basis = entry['world_design_basis']
    cards = basis['members']
    kept = [card for card in cards if card['key'] in keys]
    if not kept:
        return None
    if len(kept) == len(cards):
        return entry
    placements = entry['output']['placements']
    indices = sorted({p['path'][1] for p in placements})
    allowed = {i for i, card in zip(indices, cards, strict=True) if card['key'] in keys}
    subset = {**entry, 'world_design_basis': {**basis, 'members': kept}, 'parent_delivery_id': entry['id'],
              'output': {**entry['output'], 'placements': [p for p in placements if p['path'][1] in allowed]}}
    subset['id'] = 'pm:' + content_sha256(subset)[:32]
    return subset


def inherited(package: dict) -> list[dict]:
    old=package.get('parent_material_work') or {}
    if not package.get('parent'):
        return []
    direct = outputs(old.get('stages', []), parent=package['parent'], selected_direction=old.get('selected_direction'))
    world = next((r for r in old.get('stages', []) if r['stage'] == 'world_design'), None)
    if world is None:
        return direct
    updated = {m['key'] for entry in direct for m in entry.get('world_design_basis', {}).get('members', [])}
    current = {m['key']: m for m in world['products'].get('members', []) if m['kind'] == 'world'}
    # An intervening volume may have preserved a book rule without executing its source method again.
    carried = [remaining for entry in old.get('production_method_parents', [])
               if (cards := entry.get('world_design_basis', {}).get('members'))
               and (remaining := retained_world(entry, {m['key'] for m in cards if m['key'] not in updated and current.get(m['key'], m) == m}))]
    return list({r['id']: r for r in [*carried, *direct]}.values())


def deliveries(stage: str,previous: dict,parents: list[dict]) -> list[dict]:
    local = outputs(list(previous.values()))
    replaced = {card['key'] for entry in local for card in entry.get('world_design_basis', {}).get('members', [])}
    available = []
    for entry in parents:
        cards = entry.get('world_design_basis', {}).get('members', [])
        if cards and replaced:
            entry = retained_world(entry, {m['key'] for m in cards} - replaced)
        if entry is not None:
            available.append(entry)
    available.extend(local)
    result=[]
    for item in available:
        consumers={d['consumer'] for d in item['downstream']}
        if (stage in consumers or stage=='scene_design' and consumers&{'writer','review','acceptance'}
                or item.get('world_design_basis') and stage in ('plot_design', 'scene_design')):
            result.append(item)
    # Distinct scope/producer IDs remain separate; repeated records never double-charge a receipt.
    return list({r['id']:r for r in result}.values())


def scene_checks(session: dict,scene: str) -> list[dict]:
    previous={};parents=session.get('production_method_parents',[]);result=[];seen=set()
    for record in session.get('stages',[]):
        available=deliveries(record['stage'],previous,parents)
        by_id={r['id']:r for r in available}
        for receipt in record['products'].get('_method_receipts',[]):
            source=by_id[receipt['id']]
            if _narration_design_only(source, record['stage']):
                continue
            for guide in receipt['scene_guidance']:
                if guide['scene']!=scene:continue
                ident='method:'+receipt['id']+':'+record['stage']+':'+scene
                if ident in seen:continue
                seen.add(ident);result.append(check(ident,source,guide,receipt))
        for source in outputs([record]):
            if _narration_design_only(source, record['stage']):
                continue
            for guide in source['output']['scene_guidance']:
                if guide['scene']==scene:result.append(check('method:'+source['id']+':'+scene,source,guide,source['output']))
        previous[record['stage']]=record
    return result


def _narration_design_only(source: dict, stage: str) -> bool:
    # For a narration method the scene card feeds expression design. Only the
    # checked beat there is reader-facing; a designer's intermediate note can
    # contain another person's motivation or wording for a different passage.
    return ('narration' in source['method']['body'].get('tasks', ())
            and source['definition']['stage'] in ('scene_design', 'expression_design')
            and stage != 'expression_design')


def check(ident: str,source: dict,guide: dict,artifact: dict) -> dict:
    pin=source['method']
    return {'id':ident,'profile':'method_work','binding':{'observable':guide['observable'],'check':guide['check']},
        **({'selection_origin': 'ai_world'} if source.get('world_design_basis') else {}),
        'production_method':{'id':pin['id'],'version':pin['version'],'body_sha256':pin['body_sha256'],
                             'structure_origin':pin['structure_origin']},
        'method_operation':pin['body']['operations'],'method_artifact':artifact,'method_definition':pin['body'],
        'verification_scope':'current_scene_only','declared_method_scopes':pin['body']['scopes'],
        'project_output':source['output'],'acceptance':source['acceptance'],
        'evidence_required':'逐项按冻结方法、实际设计和本稿正文证据核对效果；设计候选或“已使用”声明不算正文证据。'}
