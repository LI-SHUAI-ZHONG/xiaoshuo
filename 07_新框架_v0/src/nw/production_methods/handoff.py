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
                if parent:entry['approved_parent']=deepcopy(parent)
                entry['id']='pm:'+content_sha256(entry)[:32];result.append(entry)
    return result


def inherited(package: dict) -> list[dict]:
    old=package.get('parent_material_work') or {}
    return outputs(old.get('stages',[]),parent=package.get('parent'),selected_direction=old.get('selected_direction')) if package.get('parent') else []


def deliveries(stage: str,previous: dict,parents: list[dict]) -> list[dict]:
    available=[*parents,*outputs(list(previous.values()))];result=[]
    for item in available:
        consumers={d['consumer'] for d in item['downstream']}
        if stage in consumers or stage=='scene_design' and consumers&{'writer','review','acceptance'}:
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
            for guide in receipt['scene_guidance']:
                if guide['scene']!=scene:continue
                ident='method:'+receipt['id']+':'+record['stage']+':'+scene
                if ident in seen:continue
                seen.add(ident);result.append(check(ident,source,guide,receipt))
        for source in outputs([record]):
            for guide in source['output']['scene_guidance']:
                if guide['scene']==scene:result.append(check('method:'+source['id']+':'+scene,source,guide,source['output']))
        previous[record['stage']]=record
    return result


def check(ident: str,source: dict,guide: dict,artifact: dict) -> dict:
    pin=source['method']
    return {'id':ident,'profile':'method_work','binding':{'observable':guide['observable'],'check':guide['check']},
        'production_method':{'id':pin['id'],'version':pin['version'],'body_sha256':pin['body_sha256'],
                             'structure_origin':pin['structure_origin']},
        'method_operation':pin['body']['operations'],'method_artifact':artifact,'method_definition':pin['body'],
        'verification_scope':'current_scene_only','declared_method_scopes':pin['body']['scopes'],
        'project_output':source['output'],'acceptance':source['acceptance'],
        'evidence_required':'逐项按冻结方法、实际设计和本稿正文证据核对效果；设计候选或“已使用”声明不算正文证据。'}
