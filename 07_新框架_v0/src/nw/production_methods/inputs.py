"""Resolve real prerequisites; proposed upstream products require author approval."""
from copy import deepcopy

from nw.materials.phase_routes import product_ref
from nw.task_models import content_sha256


def registry(package: dict,products: dict, *, ai_world: bool = False) -> dict:
    result={'brief':{'kind':'brief','status':'author_input','ref':{'id':package['brief']['project_id'],
        'version':package['brief']['version'],'sha256':content_sha256(package['brief'])},'value':package['brief']}}
    if package.get('branch_head') is not None:
        result['accepted_state']={'kind':'accepted_state','status':'approved','ref':{'head':package['branch_head'],
            'sha256':content_sha256(package.get('accepted_state',[]))},'value':package.get('accepted_state',[])}
    if package.get('parent'):
        result['parent_outline']={'kind':'parent_outline','status':'approved','ref':{'id':package['parent']['card_id'],
            'version':package['parent']['version'],'sha256':content_sha256(package['parent'])},'value':package['parent']}
        for row in (package.get('parent_material_work') or {}).get('stages',[]):
            result[row['stage']]={'kind':row['stage'],'status':'approved_parent','ref':{
                **product_ref(row),'parent':result['parent_outline']['ref']},'value':row['products']}
    status = 'frozen_upstream' if ai_world else 'proposed_requires_author'
    for stage,row in products.items():
        result[stage]={'kind':stage,'status':status,'ref':product_ref(row),'value':row['products']}
    return result


def binding(pin: dict,stage: str,inputs: dict) -> dict:
    body=pin['body'];outputs=[o for o in body['outputs'] if o['stage']==stage]
    keys={o['key'] for o in outputs};ops=[o for o in body['operations'] if set(o['output_keys'])&keys]
    needed={k for op in ops for k in op['input_keys']};requirements=[p for p in body['prerequisites'] if p['key'] in needed]
    bound={};missing=[]
    for item in requirements:
        actual=inputs.get(item['input_kind'])
        if actual:bound[item['key']]=deepcopy(actual)
        else:missing.append({'key':item['key'],'input_kind':item['input_kind'],'artifact':item['artifact'],'requirement':item['requirement']})
    return {'method':pin,'outputs':outputs,'operations':ops,'inputs':bound,'missing':missing,
            'status':'return_design' if missing else 'needs_author_applicability_review'}
