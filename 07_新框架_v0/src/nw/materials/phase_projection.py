"""Assemble actual step outputs; never invent story content during assembly."""
from copy import deepcopy
from nw.materials.phase_routes import POLICY,STAGED_POLICIES,REQUIRES,phase_order,product_ref
from nw.materials.phase_contract import validate_phase,require
from nw.materials.phase_scene_checks import anchor_beat_observable, selected_checks
from nw.materials.scene_actions import MULTI_ACTION_POLICY, action_choice, selected_action_ids
from nw.materials.phase_context import visible_facts
from nw.materials.network_followup import BASIS_STAGE, verify_followup
from nw.materials.network_workflow import EARLY_POLICY
from nw.story_state import IDENTITY_STATUS_PREFIX
from nw.task_models import canonical,content_sha256


def verify_chain(session: dict) -> None:
    require(session.get('policy') in STAGED_POLICIES,'unknown stage binding policy')
    records=session.get('stages',[]);order=phase_order(session['scope'])
    require([row['stage'] for row in records]==order,'missing, repeated or out-of-order creation stages')
    sources={row['source']['id']:row for row in session['sources']};products={}
    screening=session['context'].get('dynamic_screening')
    for row in records:
        product_ref(row)
        from nw.materials.semantic_handoff import input_stages
        dependencies=input_stages(row['stage'],products,dynamic_screening=bool(screening))
        if session['policy']=='artifact-stage-binding-v3':
            legacy={'state_transition':('character_design','static_relations','scene_design'),
                'state_propagation':('world_design','character_design','static_relations','scene_design','state_transition')}
            saved=tuple(ref.get('stage') for ref in row['inputs'])
            if saved==legacy.get(row['stage']):dependencies=list(saved)
        expected=[product_ref(products[name]) for name in dependencies]
        require(canonical(row['inputs'])==canonical(expected),'upstream product version changed or was omitted')
        selected=[sources[ident] for ident in row['source_ids']]
        context={**session['context'],'method_sources':session['sources'],
                 'legacy_replay':session['policy']=='artifact-stage-binding-v3',
                 'allowed_input_stages':dependencies,
                 'accepted_state':visible_facts(row['stage'],products,session['context'])}
        if session['policy']==POLICY:
            context.update(require_semantics=True,semantic_contracts=session.get('semantic_contracts',[]))
        if context.get('network_prerequisite_policy') and row['stage']=='plot_design':
            prepared = row.get('prepared_static_sources', [])
            require(prepared == context.get('prepared_static_sources') and set(prepared) <= set(row['source_ids']),
                    'static prerequisite input sources changed or were not offered')
        if context.get('early_network_policy') == EARLY_POLICY and row['stage'] == 'static_relations':
            prepared = row.get('prepared_static_sources')
            require(isinstance(prepared, list) and prepared == context.get('early_static_sources')
                    and set(prepared) <= set(row['source_ids']), 'early static prerequisite sources changed or were not offered')
        if context.get('binding_policy'):
            require(canonical(row.get('binding_reviews'))==canonical({ident:session['context']['binding_reviews'][ident]
                    for ident in row['source_ids'] if ident in session['context']['binding_reviews']}),
                    'source binding review disappeared from stage')
            selection=row.get('source_selection',{})
            require(selection.get('before_stage')==row['stage'] and
                canonical(selection.get('upstream'))==canonical(row['inputs']) and
                canonical(selection.get('offered'))==canonical([s['source'] for s in selected]) and
                canonical(selection.get('selected'))==canonical([s['source'] for s in selected
                    if s['source']['id'] in {u['source_id'] for u in row['products']['_uses']}]) and
                selection.get('control_review_sha256')==session['context'].get('retrieval_control',{}).get('review',{}).get('sha256'),
                'pre-step source selection trace changed or was omitted')
        from nw.production_methods import runtime as project_methods
        raw={'stage':row['stage'],'products':row['products']};clean,_=project_methods.split(raw)
        step_products = verify_followup(row, products, sources, context, session.get('calls', []))
        if BASIS_STAGE in step_products:
            context['allowed_input_stages'] = [*dependencies, BASIS_STAGE]
        validate_phase(clean,row['stage'],step_products,selected,context)
        plan=row.get('production_methods')
        if session.get('production_method_policy'):
            require(plan is not None,'project method selection and prerequisites were removed')
        elif plan is not None:raise ValueError('PROJECT_METHOD: unrequested method execution')
        project_methods.validate_output(raw,row['stage'],products,plan,session.get('production_method_parents',[]))
        if session.get('governance'):
            from nw.materials.governance_runtime import verify_stage_governance
            verify_stage_governance(session['governance'],row.get('governance'),row['stage'],
                row['products'],products,selected,session['context'])
        if screening and row['stage']=='bind_scope':
            from nw.materials.dynamic_screening import screening_report

            report=screening_report({**products,row['stage']:row},screening)
            require(not report['violations'] and canonical(report)==canonical(row.get('dynamic_screening')),
                    'dynamic screening report changed or exceeded the source limit')
        products[row['stage']]=row


def compile_candidates(session: dict) -> list[dict]:
    products={row['stage']:row['products'] for row in session['stages']}
    binder=products['bind_scope'];scope=session['scope']
    proof={'session_id':session['id'],'stage_uses':[product_ref(row) for row in session['stages']]}
    directions=products['plot_design']['directions'];result=[]
    for body in directions:
        members=[];chapters=[]
        if scope!='book' or session.get('production_method_policy'):
            for stage in ('world_design','character_design','plot_design',*(['scene_design'] if scope!='book' else [])):
                members.extend(deepcopy(products[stage]['members']))
        if scope!='book':
            scenes={row['key']:row for row in members if row['kind']=='scene'}
            actions={row['id']:row for row in products['action_design']['candidates']}
            selected=selected_action_ids(products['scene_design'])
            multi_actions=session.get('context', {}).get('multi_action_policy')==MULTI_ACTION_POLICY
            for scene, sequence in selected.items():
                scenes[scene]['body']['choice']=(action_choice([actions[ident] for ident in sequence]) if multi_actions
                                                else actions[sequence[-1]]['action'])
            for patch in products['state_transition']['patches']:
                target=scenes[patch['scene']]['body'];chosen=target['choice']
                repeated=multi_actions and len(selected[patch['scene']])>1 and any(
                    actions[ident]['action']==patch['choice'] for ident in selected[patch['scene']])
                target['choice']=chosen if chosen==patch['choice'] or repeated else chosen+'；'+patch['choice']
                target['planned_result']=patch['planned_result']
            chapters=deepcopy(products['scene_design']['chapters'])
        candidate={'kind':'plot','body':deepcopy(body),'members':members,'chapters':chapters,
                   'open_world_rules':list(products['world_design']['unknowns']),'material_work':deepcopy(proof)}
        if binder['material_bindings']:candidate['material_bindings']=deepcopy(binder['material_bindings'])
        if binder['process_bindings']:candidate['process_bindings']=deepcopy(binder['process_bindings'])
        from nw.production_methods.assembly import verify as verify_method_assembly
        verify_method_assembly(candidate,session)
        result.append(candidate)
    return result


def expand_output(raw: dict,package: dict) -> dict:
    session=package.get('material_work')
    if not session or session.get('policy') not in STAGED_POLICIES:return raw
    verify_chain(session)
    expected=compile_candidates(session)
    require(canonical(expected)==canonical(session['candidates']),'compiled products differ from the frozen candidate assembly')
    expected_refs=[content_sha256(row) for row in expected]
    require(raw.get('scope')==session['scope'] and isinstance(raw.get('candidate_cards'),list),'wrong assembly scope')
    refs=[]
    for claim in raw['candidate_cards']:
        require(isinstance(claim,dict) and set(claim)=={'kind','body'} and claim['kind']=='plot'
                and isinstance(claim['body'],dict) and set(claim['body'])=={'assembly_ref'},'assembly may only reference completed products')
        refs.append(claim['body']['assembly_ref'])
    require(refs==expected_refs,'model tried to replace or omit completed design products')
    return {'scope':session['scope'],'candidate_cards':deepcopy(expected)}


def validate_candidate(candidate: dict,session: dict) -> None:
    verify_chain(session)
    require(any(canonical(candidate)==canonical(row) for row in session['candidates']),
            'candidate no longer matches the actual staged products')


def method_checks(session: dict,scene: str,ids: dict | None=None) -> list[dict]:
    records={row['stage']:row for row in session['stages']};sources={row['source']['id']:row for row in session['sources']}
    context=session.get('context',{})
    result=selected_checks(records,scene,ids,context)
    multi_actions=(context.get('multi_action_policy')==MULTI_ACTION_POLICY and len(selected_action_ids(
        records.get('scene_design',{}).get('products',{})).get(scene,[]))>1)
    if session.get('production_method_policy'):
        from nw.production_methods.handoff import scene_checks
        result+=scene_checks(session,scene)
    if session.get('policy')==POLICY:
        from nw.materials.semantic_application import make_semantic_checks
        result+=make_semantic_checks(session,scene,ids)
    for index,guide in enumerate(records['bind_scope']['products']['method_guidance']):
        if session.get('policy')==POLICY:continue
        if guide.get('scene')!=scene:continue
        require(set(guide)=={'scene','source_ids','observable','check'},'invalid current-scene method guidance')
        linked=[row for row in session['stages'] if any(use['source_id'] in guide['source_ids'] for use in row['products']['_uses'])]
        require(bool(linked) and set(guide['source_ids'])<=sources.keys(),'scene method has no prior stage execution')
        obligations=[{'id':f'phase:{ident}','text':sources[ident]['original_text'],'source_id':ident} for ident in guide['source_ids']]
        result.append({'id':f'work:phase:{scene}:{index}','profile':'method_work',
            'binding':{'observable':guide['observable'],'check':guide['check'],
                       'source_scope':{o['id']:{'disposition':'required','reason':'核对已在正确阶段执行的方法'} for o in obligations}},
            'source_contract':{'obligations':obligations},
            'method_sources':[{'source':sources[i]['source'],'original_quotes':[sources[i]['original_text']]} for i in guide['source_ids']],
            'method_artifact':[{'stage':r['stage'],'product_sha256':r['sha256'],'products':r['products']} for r in linked],
            'evidence_required':'以已生成的前置、方法原义和实际阶段产物核对当前正文效果；计划不作为已发生事实。'})
    # These are actual model products even when no source is applicable at a
    # step. They must not disappear between design, drafting and review.
    for stage,field in (('anchor_design','beats'),('expression_design','guidance')):
        for index,guide in enumerate(records.get(stage,{}).get('products',{}).get(field,[])):
            if guide['scene']!=scene:continue
            observable=guide['observable']
            if stage=='anchor_design' and multi_actions:
                observable=anchor_beat_observable(guide,records,scene,ids)
            result.append({'id':f'work:stage:{stage}:{scene}:{index}','profile':'method_work',
                'binding':{'observable':observable,'check':guide['check']},
                'method_artifact':guide,
                'evidence_required':'核对当前场景是否实际呈现已设计的动作、节拍和表达效果。'})
    ids=ids or {}
    changes=records.get('state_transition',{}).get('products',{})
    patches={p['scene']:p for p in changes.get('patches',[])}
    scene_body=next((row['body'] for row in records.get('scene_design',{}).get('products',{}).get('members',[]) if row['key']==scene),{})
    for index,transition in enumerate(changes.get('transitions',[])):
        if transition['scene']!=scene:continue
        patch=patches[scene];entity=ids.get(transition['entity'],transition['entity'])
        state=[{'entity_id':entity,'predicate':key,'holder':'WORLD',
                'new_value':value}
               for key,value in transition['after_state'].items()
               if canonical(value)!=canonical(transition['before_state'].get(key))]
        visible_target = {key: value for key, value in transition['after_state'].items()
                          if not key.startswith(IDENTITY_STATUS_PREFIX)}
        result.append({'id':f'work:state:{scene}:{index}','profile':'method_work',
            'binding':{'observable':canonical({'external_action':transition['action'],'choice':patch['choice'],
                'candidate_result':patch['planned_result'],'required_candidate_after_state':visible_target,
                'presentation_boundary':scene_body.get('allowed_disclosure','仅本场POV可见或可知内容'),
                'state_policy':'这是当前场景应呈现的候选变化，按POV和披露边界设计表现，不是已接受事实；不把未来或幕后信息当作已知。'}),
                'check':canonical({key:transition[key] for key in ('cost','failure','continuity')}),'state':state},
            'method_artifact':transition,
            'evidence_required':'候选变化必须在本稿有行动、后果和独立证据，再交给状态提取核对；候选前状态不得冒充已接受事实。'})
    return result


def verify_current_state(session: dict,scene: str,ids: dict,facts: list) -> None:
    """Check the actual story-time view, never the latest planning replay."""
    known={(f.entity_id,f.predicate,f.holder):f.value for f in facts if f.claim=='fact'}
    changes=next((r['products'] for r in session['stages'] if r['stage']=='state_transition'),{})
    for transition in changes.get('transitions',[]):
        if transition['scene']!=scene:continue
        entity=ids.get(transition['entity'],transition['entity'])
        for key,value in transition['before_state'].items():
            address=entity,key,'WORLD'
            if address in known and canonical(known[address])!=canonical(value):
                raise ValueError('MATERIAL_PRECONDITION: native candidate before-state conflicts with actual story-time facts')
        for key,value in transition['after_state'].items():known[entity,key,'WORLD']=value
