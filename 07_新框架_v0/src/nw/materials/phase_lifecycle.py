"""Keep conditional alternatives distinct from selected scene obligations."""
from nw.task_models import _text


def selected_refs(products: dict) -> dict[str,set[str]]:
    scene=products.get('scene_design',{}).get('products',{})
    anchor=products.get('anchor_design',{}).get('products',{})
    return {'event_design':{'event_candidate:'+r['event'] for r in scene.get('selected_events',[])},
            'action_design':{'action:'+r['action'] for r in scene.get('selected_actions',[])},
            'state_propagation':{'propagation:'+r['propagation'] for r in anchor.get('selected_propagations',[])}}


def writing_sources(products: dict,current_uses: list[dict]) -> set[str]:
    chosen=selected_refs(products);result={u['source_id'] for u in current_uses}
    for stage,record in products.items():
        for use in record['products'].get('_uses',[]):
            if stage not in chosen or set(use['output_refs'])&chosen[stage]:result.add(use['source_id'])
    return result


def requirements_for(stage: str,products: dict) -> list[dict]:
    return [r for r in products.get('static_relations',{}).get('products',{}).get('requirements',[])
            if r['target_stage']==stage]


def validate_requirements(stage: str,value: dict,products: dict,refs: set[str]) -> None:
    expected={r['id'] for r in requirements_for(stage,products)}
    applied=value.get('_requirements',[]);seen=set()
    valid=isinstance(applied,list)
    if valid:
        for row in applied:
            valid=(isinstance(row,dict) and set(row)=={'id','operation','output_refs'}
                   and _text(row['id']) and row['id'] in expected-seen
                   and _text(row['operation']) and len(''.join(row['operation'].split()))>=8
                   and isinstance(row['output_refs'],list) and bool(row['output_refs'])
                   and all(_text(ref) and ref in refs for ref in row['output_refs']))
            if not valid:break
            seen.add(row['id'])
    if not valid or seen!=expected:
        raise ValueError('MATERIAL_STAGE: directed method requirements need actual downstream products')


def validate_selected_requirements(stage: str,value: dict,products: dict,context: dict | None=None) -> None:
    mappings=({'action_design':('selected_actions','action','action'),
               'event_design':('selected_events','event','event_candidate')} if stage=='scene_design' else
              {'state_propagation':('selected_propagations','propagation','propagation')} if stage=='anchor_design' else {})
    people={r['key'] for r in products.get('character_design',{}).get('products',{}).get('members',[])}
    people|={r['card_id'] for r in (context or {}).get('approved_cards',[]) if r['kind']=='character'}
    for target,(selection,key,prefix) in mappings.items():
        outputs=products.get(target,{}).get('products',{})
        candidates={r['id']:r for r in outputs.get('candidates',[])}
        chosen={r[key] for r in value.get(selection,[]) if r[key] in candidates}
        for requirement in requirements_for(target,products):
            bound={r[7:] for r in requirement['project_refs'] if r.startswith('member:') and r[7:] in people}
            relevant={ident for ident in chosen if not bound or bound&{
                candidates[ident].get('actor'),candidates[ident].get('source_entity'),
                candidates[ident].get('target_entity'),*candidates[ident].get('actors',[])}}
            applied=next((r for r in outputs.get('_requirements',[]) if r['id']==requirement['id']),{})
            if not {prefix+':'+ident for ident in relevant}<=set(applied.get('output_refs',[])):
                raise ValueError('MATERIAL_STAGE: selected design abandoned its directed method requirement')
