"""Validate actual upstream products before executing a creation method."""
from nw.cards import _body
from nw.materials.phase_routes import REQUIRES,readiness,product_ref,route_method
from nw.materials.scene_actions import MULTI_ACTION_POLICY
from nw.story_state import IDENTITY_STATUS_PREFIX, validate_identity_status
from nw.task_models import _text,canonical
from nw.materials.template_contract import extra_refs,validate_extra,validate_template_uses
from nw.materials.phase_lifecycle import writing_sources,validate_requirements,validate_selected_requirements
from nw.materials.semantic_products import (validate_plot_products,validate_dynamic_dependencies,
    validate_anchor_products,validate_static_bindings,validate_early_static)

FIELDS={
 'type_selection':{'selection','concepts','boundaries'},
 'type_adaptation':{'adaptations','focuses','boundaries'},
 'world_design':{'members','limitations','unknowns'},
 'character_design':{'members','states','capabilities'},
 'static_relations':{'relations','requirements'},
 'plot_design':{'directions','members','reader_plan','promise_plan','event_nodes'},
 'event_design':{'candidates'},'action_design':{'candidates','waiting'},
 'scene_design':{'members','chapters','events','selected_events','selected_actions'},
 'state_transition':{'patches','transitions'},
 'state_propagation':{'candidates','waiting'},
 'anchor_design':{'beats','selected_propagations'},'expression_design':{'guidance'},
 'bind_scope':{'material_bindings','process_bindings','method_guidance'},
}


def require(condition: bool,reason: str) -> None:
    if not condition:raise ValueError('MATERIAL_STAGE: '+reason)


def _method_stages(source: dict,context: dict) -> list[str]:
    if context.get('binding_policy')=='workflow-source-binding-v1':
        from nw.materials.binding_reviews import allows_stage_candidate
        review=context.get('binding_reviews',{}).get(source['source']['id'],{})
        if review:
            return [u['stage'] for u in review['uses'] if context.get('scope') in
                    u.get('scopes',['book','volume','chapter','scene','replan'])]
        from nw.materials.network_workflow import prepared_static_source
        stages = route_method(source)['stages']
        stages += [stage for stage in ('static_relations', 'plot_design')
                   if stage not in stages and prepared_static_source(source, stage, context)]
        return [stage for stage in stages
                if allows_stage_candidate(source,stage,context)]
    if not context.get('legacy_replay'):return route_method(source)['stages']
    from nw.materials.phase_routes import ROUTES,TEMPLATE_STAGES
    ref=source['source']
    template=next((v for k,v in TEMPLATE_STAGES.items() if ref['key'].startswith(k)),None)
    return [template] if template else list(ROUTES.get(ref['profile'],('governance',)))


def entity_ids(products: dict,context: dict) -> set[str]:
    known={row['card_id'] for row in context.get('approved_cards',[]) if row['kind'] in ('world','character','promise')}
    for stage in ('world_design','character_design','plot_design'):
        known.update(row['key'] for row in products.get(stage,{}).get('products',{}).get('members',[]))
    return known


def output_refs(stage: str,value: dict) -> set[str]:
    refs={f'member:{row["key"]}' for row in value.get('members',[])}
    if stage == 'character_design':
        refs.update(f'assignment:{row["demand"]}' for row in value.get('cast_assignments', []))
    if stage == 'character_design' and 'cast_assignments' in value:
        created = {m['key'] for m in value.get('members', ())}
        refs.update('capability:' + r['entity'] for r in value.get('capabilities', ()) if r['entity'] not in created)
    refs|={f'scene:{row["scene"]}' for key in ('patches','transitions','beats','guidance') for row in value.get(key,[])}
    if stage=='scene_design':refs|={f'scene:{row["key"]}' for row in value['members']}
    refs|={f'direction:{index}' for index,_ in enumerate(value.get('directions',[]))}
    refs|={f'relation:{row["id"]}' for row in value.get('relations',[])}
    refs|={f'relation:{row["id"]}' for row in value.get('static_bindings',[])}
    for key in ('selection','boundaries','limitations','unknowns','reader_plan','promise_plan'):
        if value.get(key):refs.add(key)
    if stage=='bind_scope':
        if value.get('material_bindings') or value.get('process_bindings'):refs.add('bindings')
        refs|={'guidance:'+row['scene'] for row in value['method_guidance']}
    return refs|extra_refs(stage,value)


def _members(rows: object,kinds: set[str],existing: set[str]) -> set[str]:
    require(isinstance(rows,list),'members must be a list')
    seen=set()
    for row in rows:
        require(isinstance(row,dict) and set(row)=={'key','kind','body'} and _text(row['key'])
                and row['key'] not in seen|existing and row['kind'] in kinds,'invalid or duplicate stage member')
        _body(row['kind'],row['body']);seen.add(row['key'])
        if row['kind'] in ('character','world'):
            require('visibility' in row['body'],'entity design must explicitly separate visible settings and private information')
    return seen


def validate_phase(raw: dict,stage: str,products: dict,sources: list[dict],context: dict) -> None:
    state=readiness(stage,products,context.get('scope','chapter'),
                    planning_hierarchy=context.get('planning_hierarchy', False))
    if state['missing']:
        raise ValueError('MATERIAL_WAITING_INPUTS: '+stage+' needs '+','.join(state['missing']))
    for key in (products if stage=='bind_scope' else REQUIRES[stage]):
        product_ref(products[key])
    if stage=='type_adaptation':
        context={**context,'type_selection':products['type_selection']['products']}
    try:_validate(raw,stage,products,sources,context)
    except (KeyError,TypeError,ValueError) as exc:
        if str(exc).startswith(('MATERIAL_STAGE:','MATERIAL_WAITING_INPUTS:')):raise
        raise ValueError('MATERIAL_STAGE: '+str(exc)) from exc


def _validate(raw: dict,stage: str,products: dict,sources: list[dict],context: dict) -> None:
    from nw.materials import planning_hierarchy
    from nw.materials.type_network import POLICY as TYPE_NETWORK_POLICY, validate_adaptation_inputs

    require(isinstance(raw,dict) and set(raw)=={'stage','products'} and raw['stage']==stage,'wrong stage output')
    value=raw['products']
    volume_outline = planning_hierarchy.volume_outline(context.get('scope','chapter'),
                                                        context.get('planning_hierarchy', False))
    from nw.materials import cast_demands, cast_distribution_plan, chapter_progress, passage_sequence
    passage_enabled = context.get('passage_policy') == passage_sequence.POLICY
    from nw.materials import passage_craft
    craft_enabled = context.get('passage_craft_policy') == passage_craft.POLICY and context.get('scope') != 'book'
    cast_distribution = context.get('cast_distribution_policy') == cast_distribution_plan.POLICY
    cast_enabled = context.get('cast_demand_policy') == cast_demands.POLICY
    progress_enabled = context.get('chapter_progress_policy') in chapter_progress.POLICIES
    require('<填写' not in canonical(value),'unfilled transport shape is not an actual project product')
    type_network_inputs = stage == 'type_selection' and context.get('type_network_policy') == TYPE_NETWORK_POLICY
    require(isinstance(value,dict) and FIELDS[stage]|{'_uses'}<=value.keys()
            and not value.keys()-FIELDS[stage]-{'_uses','_excluded','_requirements','_criteria'}
            -({'static_bindings'} if stage=='plot_design' else set())-{'_governance','_receipts'}
            -({'scene_progress'} if progress_enabled and stage == 'scene_design' else set())
            -({'cast_demands'} if cast_enabled and stage == 'world_design' else set())
            -({'cast_assignments'} if cast_enabled and stage == 'character_design' else set())
            -({'continuations'} if progress_enabled and stage == 'plot_design' and context.get('chapter_openings') else set())
            -({'adaptation_inputs'} if type_network_inputs else set())
            -({'cast_events'} if cast_enabled and stage == 'plot_design' else set())
            -({'cast_payoffs'} if cast_enabled and stage == 'scene_design' else set())
            -({'cast_distribution_plan'} if cast_distribution and stage == 'scene_design' else set())
            -({'passage_choices'} if passage_enabled and stage == 'scene_design' else set())
            -({'passage_sequences'} if passage_enabled and stage == 'expression_design' else set())
            -(passage_craft.schema_fields(stage).keys() if craft_enabled else set())
            -{'preference_resolutions'}
            -({'_network_design_uses'} if context.get('design_network_policy') else set()),'wrong stage product fields')
    from nw.materials.creation_preferences import validate_resolutions, validate_selected_types

    validate_resolutions(stage, value, context)
    planning_hierarchy.validate_types(stage, value, context)
    if '_governance' in value:
        config=value['_governance']
        require(stage=='type_selection' and isinstance(config,dict) and set(config)=={'project_config'}
                and isinstance(config['project_config'],dict)
                and set(config['project_config'])=={'genre_ids','mechanism_ids','structure_ids','style_ids','tone_ids'}
                and all(isinstance(rows,list) and all(_text(ident) for ident in rows)
                        for rows in config['project_config'].values()),'invalid actual type configuration')
    entities=entity_ids(products,context)
    if stage=='type_selection':
        require(isinstance(value['selection'],list) and isinstance(value['boundaries'],list),'type choice and boundaries required')
        validate_selected_types(value, context)
        if type_network_inputs:
            validate_adaptation_inputs(value, products, context)
    elif stage=='world_design':
        _members(value['members'],{'world'},entities)
        if cast_enabled:
            cast_demands.validate_demands(value.get('cast_demands'), cast_demands.source_options(context),
                                          cast_demands.roster(context))
        require(all(isinstance(value[k],list) and all(_text(v) for v in value[k]) for k in ('limitations','unknowns')),'world limits required')
    elif stage=='character_design':
        new=_members(value['members'],{'character'},entities)
        people=new|{r['card_id'] for r in context.get('approved_cards',[]) if r['kind']=='character'}
        from nw.materials.narration import ACCESS_POLICIES, EVIDENCE_POLICY
        if context.get('narration_policy') in ACCESS_POLICIES:
            from nw.materials.cast_design import need_sources, validate_card, validate_introducer
            needs = cast_demands.source_options(context) if cast_enabled else need_sources(context, products)
            character_cards = {r['card_id']: r['body'] for r in context.get('approved_cards', []) if r['kind'] == 'character'}
            character_cards.update((r['key'], r['body']) for r in value['members'])
            for row in value['members']:
                validate_card(row['body'])
                card = row['body']['casting']
                require(card['need_ref'] in needs and card['need_quote'] in needs[card['need_ref']],
                        '新增人物须引用本项目的真实前置设计需求')
                if card['entry'] == 'other':
                    require(card['introducer'] in people - {row['key']}, '身份介绍者必须是另一位实际人物')
                    if card['introducer_source'] == 'prior':
                        prior = () if context.get('narration_policy') == EVIDENCE_POLICY else context.get('accepted_state', [])
                        validate_introducer(card, character_cards[card['introducer']], row['key'], prior)
            if context.get('scope') == 'book' and people == new:
                require(any(row['body']['casting']['standing'] == 'protagonist' for row in value['members']),
                        '本书首次设计人物未说明谁承担主角')
        require(bool(people),'character stage did not create or identify any actual character')
        if cast_enabled:
            cast_demands.validate_assignments(value, products, context)
        require(isinstance(value['states'],list),'candidate initial states required')
        for row in value['states']:
            require(set(row)=={'entity','state','status'} and row['entity'] in people
                    and isinstance(row['state'],dict) and row['status']=='candidate','initial design is a candidate, not accepted state')
    elif stage=='static_relations':
        require(isinstance(value['relations'],list),'stable relationship list required')
        seen=set()
        for row in value['relations']:
            require(set(row)=={'id','source','target','relation','condition'} and _text(row['id'])
                    and row['id'] not in seen and row['source'] in entities and row['target'] in entities
                    and _text(row['relation']) and _text(row['condition']),'stable relation needs actual project endpoints')
            seen.add(row['id'])
    elif stage=='plot_design':
        _members(value['members'],{'plot','promise','volume','chapter'},entities)
        if context.get('planning_hierarchy'):
            planning_hierarchy.validate_plot(value, context['scope'])
        validate_static_bindings(value,products,sources,context)
        require(isinstance(value['directions'],list) and 1<=len(value['directions'])<=3,'concrete direction products required')
        from nw.materials.book_direction import approved

        if approved(context):
            require(len(value['directions']) == 1, '已确认全书方向只接受一份对应的剧情深化')
        else:
            require(len(value['directions'])==1 if context.get('scope','chapter')!='book' else len(value['directions'])>=2,
                    'each detailed direction needs its own coherent scene products; book needs alternatives')
        from nw.plan_contract import _DIRECTION
        for body in value['directions']:
            _body('plot',body);require(all(_text(body.get(k)) for k in _DIRECTION),'incomplete direction product')
        if length := context.get('length_context'):
            from nw.length_plan import check_budget, check_reference, validate_direction
            for body in value['directions']:
                validate_direction(body, length)
            if context.get('scope') != 'book':
                for row in value['members']:
                    if row['kind'] == 'chapter':
                        check_reference(row['body'].get('word_budget'), length['policy'], 'chapter')
                    elif row['kind'] == 'volume':
                        check_budget(row['body'].get('word_budget'))
        require(isinstance(value['reader_plan'],list) and isinstance(value['promise_plan'],list),'reader and promise planning products required')
        if progress_enabled and context.get('chapter_openings'):
            chapter_progress.validate_continuations(value, context['chapter_openings'])
        for key in ('reader_plan','promise_plan'):
            require(all(_text(row) or isinstance(row,dict) and bool(row) for row in value[key]),
                    'reader/promise planning needs actual design content')
    elif stage=='scene_design':
        _members(value['members'],{'scene'},entities)
        require(bool(value['members']) and isinstance(value['chapters'],list) and bool(value['chapters']),'actual scene task products required')
        scenes={r['key']:r for r in value['members']}
        people={r['key'] for r in products['character_design']['products']['members']}
        people|={r['card_id'] for r in context.get('approved_cards',[]) if r['kind']=='character'}
        people_bodies={r['key']:r['body'] for r in products['character_design']['products']['members']}
        people_bodies.update({r['card_id']:r['body'] for r in context.get('approved_cards',[]) if r['kind']=='character'})
        for row in scenes.values():
            body=row['body'];require(body['pov'] in people and set(body['characters'])<=people,'scene has no existing viewpoint/characters')
            from nw.materials.narration import ACCESS_POLICIES, PERSONS
            if context.get('narration_policy') in ACCESS_POLICIES:
                require(body.get('narrative_person') in PERSONS, '本场缺少已选的叙述人称')
            from nw.plan_contract import _SCENE_TEXT
            require(all(_text(body.get(key)) for key in _SCENE_TEXT)
                    and set(body.get('character_goals',{}))=={body['pov'],*body['characters']},
                    'scene design must finish the actual task before downstream methods')
            require(not any(label in body['choice'] for label in ('必须作出应对选择','需要作出选择','待选择','待定')),
                    'scene action choice is not yet an actual upstream product')
            for person in {body['pov'],*body['characters']}:
                actor=people_bodies[person]
                require(actor.get('visibility')=='public' or actor.get('visibility')=='holders'
                        and body['pov'] in actor.get('holders',[]),'scene character is hidden from the actual viewpoint')
        from nw.plan_contract import _chapters
        all_members={r['key']:r for stage_name in ('world_design','character_design','plot_design')
                     for r in products[stage_name]['products']['members']}
        all_members.update(scenes)
        _chapters(value['chapters'],context.get('scope','chapter'),all_members)
        planning_hierarchy.validate_scene_handoff(value, context)
        if cast_distribution:
            cast_distribution_plan.validate(value, products, context)
        if passage_enabled:
            passage_sequence.validate_choices(value, products, context.get('passage_references', []))
        if context.get('narration_policy') in ACCESS_POLICIES:
            from nw.materials.cast_design import entry_bases
            from nw.materials.narration import EVIDENCE_POLICY
            from nw.materials.phase_context import new_character_keys
            entry_bases(value, [(k, 'character', v) for k, v in people_bodies.items()],
                        context.get('cast_previous_appearances', {}), context.get('accepted_state', []),
                        new_people=new_character_keys(products, context) if context.get('narration_policy') == EVIDENCE_POLICY else None)
        if progress_enabled:
            chapter_progress.validate(value, products, context)
        if length := context.get('length_context'):
            from nw.length_plan import validate_allocations
            validate_allocations(value['chapters'], all_members, length)
        require(isinstance(value['events'],list),'candidate events must be explicit')
        ids=set()
        for event in value['events']:
            require(set(event)=={'id','scene','entity','trigger','before_state'} and _text(event['id'])
                    and event['id'] not in ids and event['scene'] in scenes and event['entity'] in entities
                    and _text(event['trigger']) and isinstance(event['before_state'],dict) and bool(event['before_state']),
                    'candidate event needs an existing entity, scene, trigger and before-state')
            ids.add(event['id'])
    elif stage=='state_transition':
        scene_product=products['scene_design']['products'];scenes={r['key'] for r in scene_product['members']}
        events={r['id']:r for r in scene_product['events']}
        require(isinstance(value['patches'],list) and isinstance(value['transitions'],list),'transition products required')
        require(len({p['scene'] for p in value['patches']})==len(value['patches'])
                and len({t['event'] for t in value['transitions']})==len(value['transitions']),
                'a state event or scene patch may not be repeatedly emitted')
        for patch in value['patches']:
            require(set(patch)=={'scene','choice','planned_result'} and patch['scene'] in scenes
                    and _text(patch['choice']) and _text(patch['planned_result']),'transition cannot create missing scenes or entities')
            require(not any(label in patch['choice'] for label in ('必须作出应对选择','需要作出选择','待选择','待定')),
                    'external action choice is still unresolved')
            if progress_enabled:
                body = next(row['body'] for row in scene_product['members'] if row['key'] == patch['scene'])
                progress = next(row for row in scene_product['scene_progress'] if row['scene'] == patch['scene'])
                require(chapter_progress.permits_unchanged_story(progress['change'],context)
                        or patch['planned_result'].strip() != body['entering_state'].strip(),
                        '状态补丁不能取消本场已经设计的实际推进')
        for transition in value['transitions']:
            require(set(transition)=={'scene','entity','event','before_state','action','after_state','cost','failure','continuity'}
                    and transition['scene'] in scenes and transition['entity'] in entities
                    and transition['event'] in events,'state method has no actual upstream entity/event')
            event=events[transition['event']]
            body=next(r['body'] for r in scene_product['members'] if r['key']==transition['scene'])
            require(transition['action'] not in {body.get('entering_state'),body.get('goal')},
                    'state method repeated the entering state instead of selecting an external action')
            require(not any(label in transition[key] for key in ('action','cost','failure','continuity')
                            for label in ('<填写','写出实际','失败条件和处理','事件到后续状态的连续性检查')),
                    'method field labels are not actual project operations')
            require(transition['scene']==event['scene'] and transition['entity']==event['entity']
                    and canonical(transition['before_state'])==canonical(event['before_state']),
                    'state method did not consume the frozen event before-state')
            require(isinstance(transition['after_state'],dict) and any(canonical(v)!=canonical(transition['before_state'].get(k))
                    for k,v in transition['after_state'].items())
                    and all(_text(transition[k]) for k in ('action','cost','failure','continuity')),'causal change and continuity must be designed')
            require(any(p['scene']==transition['scene'] for p in value['patches']),
                    'state transition needs an actual scene choice and result patch')
            for predicate, state in transition['after_state'].items():
                if isinstance(predicate, str) and predicate.startswith(IDENTITY_STATUS_PREFIX):
                    require(predicate in transition['before_state'], 'identity transition needs the explicit prior value')
                    previous = transition['before_state'][predicate]
                    if previous is not None:
                        validate_identity_status(predicate, 'WORLD', previous)
                    validate_identity_status(predicate, 'WORLD', state)
        if any(s['source']['key'].startswith('TDR_TEMPLATE_003') for s in sources if s['source']['id'] in {u['source_id'] for u in value['_uses']}):
            require(bool(value['transitions']),'entity-state template needs an actual project transition')
    elif stage in ('anchor_design','expression_design'):
        scenes={r['key']:r for r in products['scene_design']['products']['members']}
        rows=value['beats' if stage=='anchor_design' else 'guidance']
        require(isinstance(rows,list) and bool(rows),'actual visible scene work required')
        from nw.materials import narration
        narrated = stage == 'expression_design' and context.get('narration_policy') in narration.POLICIES
        bases = narration.scene_bases(products, context) if narrated else {}
        beat_counts = dict.fromkeys(scenes, 0)
        for row in rows:
            required={'scene','observable','check'}|({'observer','object','action'} if stage=='anchor_design' else set())
            require(required<=set(row) and not set(row)-required-({'action_ref','step_index','timing','trigger_basis'}
                    if stage=='anchor_design' else {'narration'} if narrated else set()) and row['scene'] in scenes
                    and all(_text(row[k]) for k in required),'invalid scene expression product')
            if stage=='anchor_design':require(row['observer']==scenes[row['scene']]['body']['pov'],'anchor observer differs from actual viewpoint')
            if narrated:
                narration.validate_beat(row.get('narration'), scenes[row['scene']]['body'], bases[row['scene']],
                                        access=context.get('narration_policy') in narration.ACCESS_POLICIES)
                beat_counts[row['scene']] += 1
                narration.register_beat(bases[row['scene']], beat_counts[row['scene']], row)
        if narrated and context.get('narration_policy') in narration.ACCESS_POLICIES:
            from nw.materials.cast_design import validate_expression
            validate_expression(rows, scenes, bases, witnessed_entries=context.get('narration_policy') == narration.EVIDENCE_POLICY)
        require({row['scene'] for row in rows}==scenes.keys(),'a scene has no actual anchor or expression products')
        if passage_enabled and stage == 'expression_design':
            passage_sequence.validate_sequences(value, products['scene_design']['products'], context.get('passage_references', []))
    elif stage=='bind_scope':
        require(isinstance(value['material_bindings'],dict) and isinstance(value['process_bindings'],dict)
                and isinstance(value['method_guidance'],list),'scope binding products required')
        from nw.materials.binding_assembly import validate_assembly
        validate_assembly(value,products,sources,context)
        if volume_outline:
            require(not any(value[key] for key in ('material_bindings', 'process_bindings', 'method_guidance')),
                    '卷纲只交付阶段设计，正文绑定在具体场景环节完成')
        elif context.get('scope','chapter')!='book':
            scenes={r['key'] for r in products['scene_design']['products']['members']}
            uses=[u for row in products.values() for u in row['products']['_uses']]+value['_uses']
            used_ids=writing_sources(products,value['_uses']);covered=set();placements=set()
            for guide in value['method_guidance']:
                require(isinstance(guide,dict) and set(guide)=={'scene','source_ids','observable','check'}
                        and guide['scene'] in scenes and isinstance(guide['source_ids'],list)
                        and bool(guide['source_ids']) and set(guide['source_ids'])<=used_ids
                        and _text(guide['observable']) and _text(guide['check']),
                        'scene guidance needs actually executed methods and an existing scene')
                covered.update(guide['source_ids']);placements.update((i,guide['scene']) for i in guide['source_ids'])
            require(covered==used_ids,'executed methods disappeared before writing')
            for use in uses:
                if use['source_id'] not in used_ids:continue
                for ref in use['output_refs']:
                    if ref.startswith('scene:'):
                        require((use['source_id'],ref[6:]) in placements,'method lost its actual scene placement')
    require(isinstance(value['_uses'],list),'method uses must name their actual outputs')
    allowed={s['source']['id']:s for s in sources};used=set();refs=output_refs(stage,value)
    for use in value['_uses']:
        require(set(use)=={'source_id','operation','output_refs'} and _text(use['source_id'])
                and use['source_id'] in allowed and use['source_id'] not in used
                and stage in _method_stages(allowed[use['source_id']],context)
                and _text(use['operation']) and len(''.join(use['operation'].split()))>=8
                and use['operation'].strip().casefold() not in {'read_or_execute','read','execute','ready','done','completed'}
                and not use['operation'].strip().casefold().startswith(('readout_','read_source','read_original','source_state','source_sha'))
                and isinstance(use['output_refs'],list) and bool(use['output_refs'])
                and all(_text(ref) and ref in refs for ref in use['output_refs']),'method is bound to the wrong step or an absent product')
        used.add(use['source_id'])
        if stage=='plot_design':
            ref=allowed[use['source_id']]['source'];key=ref['key']
            needed=('reader_plan' if key.startswith('64.1_') or '读者情绪' in key else
                    'promise_plan' if key.startswith('45.1_') or ref['profile']=='promise_process' else None)
            if needed:
                require(bool(value[needed]) and needed in use['output_refs'],
                        'reader/foreshadow method has no actual corresponding design product')
    excluded=value.get('_excluded',[])
    require(isinstance(excluded,list),'method exclusions must be explicit')
    for row in excluded:
        require(set(row)=={'source_id','reason'} and row['source_id'] in allowed.keys()-used
                and _text(row['reason']),'unexplained or duplicate method exclusion')
        reason=row['reason'].casefold()
        if any(token in reason for token in ('template','blocked','reference','模板身份','来源资格')):
            require(any(token in reason for token in ('本项目','本场','当前任务','本次任务','所选','前置','实际输入',
                '事件','最低能力','项目中','项目没有')),'source qualification alone is not project nonapplicability')
        used.add(row['source_id'])
    require(used==allowed.keys(),'every delivered method needs an actual use or an explained exclusion')
    validate_extra(stage,value,products,sources,context)
    if craft_enabled:
        passage_craft.validate(stage,value,products,context)
    if cast_enabled:
        from nw.materials.cast_fulfillment import validate as validate_fulfillment
        validate_fulfillment(stage, value, products, context)
    validate_template_uses(stage,value,products,sources,context)
    validate_requirements(stage,value,products,output_refs(stage,value))
    validate_selected_requirements(stage,value,products,context)
    from nw.materials.network_workflow import POLICY as NETWORK_POLICY
    strict_network = context.get('network_prerequisite_policy') == NETWORK_POLICY
    check_anchor = stage == 'anchor_design' and not context.get('legacy_replay')
    multiple_actions = context.get('multi_action_policy') == MULTI_ACTION_POLICY
    if not context.get('legacy_replay'):
        from nw.materials.step_guard import validate_cross_step_consistency
        validate_cross_step_consistency(stage, value, products, context)
        if stage=='plot_design':validate_plot_products(value,sources,context)
        if check_anchor and not multiple_actions:
            validate_anchor_products(value, products, sources, context)
        if not strict_network:
            validate_dynamic_dependencies(stage,value,products,sources,context)
    from nw.materials.semantic_application import validate_semantic_applications
    validate_semantic_applications(stage,value,products,sources,context)
    if stage == 'static_relations' and not context.get('legacy_replay'):
        validate_early_static(value, products, sources, context)
    if check_anchor and multiple_actions:
        validate_anchor_products(value, products, sources, context)
    if strict_network and not context.get('legacy_replay'):
        if stage == 'plot_design':
            from nw.materials.semantic_products import validate_prepared_static
            validate_prepared_static(value, sources, context)
        validate_dynamic_dependencies(stage,value,products,sources,context)
    if context.get('scene_source_binding_policy'):
        from nw.materials.scene_source_bindings import POLICY, validate_candidate_sources, validate_scene_sources
        require(context['scene_source_binding_policy'] == POLICY, 'unknown scene source binding policy')
        validate_candidate_sources(stage, value)
        if stage == 'bind_scope' and context.get('scope', 'chapter') != 'book' and not volume_outline:
            validate_scene_sources(value, products)
    from nw.materials.semantic_handoff import validate_handoffs
    validate_handoffs(stage,value,products,context)
