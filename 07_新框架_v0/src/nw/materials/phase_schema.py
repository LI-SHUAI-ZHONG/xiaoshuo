"""Transport grammar for stage JSON; semantic validation remains independent."""
from nw.cards import _REQUIRED,_OPTIONAL,_LISTS,_MAPS
from nw.materials.phase_contract import FIELDS
from nw.materials.phase_routes import ORDER

TEXT={'type':'string','minLength':1}
ANY={'type':['string','number','boolean','object','array','null']}


def obj(fields: dict,optional: tuple=()) -> dict:
    return {'type':'object','properties':fields,'required':[k for k in fields if k not in optional],
            'additionalProperties':False}


def array(item: dict=ANY,minimum: int=0) -> dict:
    return {'type':'array','items':item,'minItems':minimum}


def strings(*keys: str) -> dict:
    return {key:TEXT for key in keys}


def card(kind: str, *, narration: bool | str = False) -> dict:
    fields={**strings(*_REQUIRED[kind]),**{k:{'type':['string','null']} for k in _OPTIONAL[kind]},
            **{k:array(TEXT) for k in (*_LISTS.get(kind,()),'holders','tags','unknowns')},
            **{k:{'type':'object','additionalProperties':TEXT} for k in _MAPS.get(kind,())},
            'visibility':{'enum':['public','holders','author_only']}}
    if kind == 'world' and not narration:
        fields.pop('history')
    from nw.materials.narration import ACCESS_POLICIES, PERSONS
    required = {*_REQUIRED[kind], 'visibility'}
    if kind == 'character' and narration in ACCESS_POLICIES:
        from nw.materials.cast_design import STANDINGS, ENTRIES, PERSON_FIELDS
        base = {'standing': {'enum': list(STANDINGS)}, **strings('public_identity', 'need_ref', 'need_quote')}
        alternatives = []
        for entry in ENTRIES:
            extra = ('clue', 'secret', 'trigger') if entry == 'withheld' else (
                ('introducer', 'introducer_basis') if entry == 'other' else ())
            alternatives.append(obj({**base, 'entry': {'const': entry}, **strings(*extra)}))
            if entry == 'other':
                alternatives[-1]['properties']['introducer_source'] = {'enum': ['prior', 'on_scene']}
                alternatives[-1]['required'].append('introducer_source')
        fields.update(**strings(*PERSON_FIELDS), casting={'anyOf': alternatives})
        required.update((*PERSON_FIELDS, 'casting'))
    if kind == 'scene':
        if narration in ACCESS_POLICIES:
            fields['narrative_person'] = {'enum': list(PERSONS)}
            required.add('narrative_person')
        else:
            fields.pop('narrative_person')
    body=obj(fields,tuple(set(fields)-required))
    return obj({'key':TEXT,'kind':{'const':kind},'body':body})


def schema(stage: str,sources: list[dict],readable: list[str]=(),inputs: dict | None=None,*,allow_requests: bool=True,
           contracts: list[dict] | None=None, type_network_inputs: bool=False, narration: bool | str=False,
           chapter_progress: bool=False, cast_demand: bool=False, cast_distribution: bool=False, passage: bool=False,
           craft: bool=False, effect_kinds=None) -> dict:
    state={'type':'object','additionalProperties':ANY,'minProperties':1}
    use=obj({**strings('source_id','operation'),'output_refs':array(TEXT,1)})
    use['properties']['operation']={'type':'string','minLength':8,'maxLength':160}
    common={'_uses':array(use),'_excluded':array(obj(strings('source_id','reason'))),
            '_requirements':array(obj({**strings('id','operation'),'output_refs':array(TEXT,1)}))}
    common['_governance']=obj({'project_config':obj({k:array(TEXT) for k in
        ('genre_ids','mechanism_ids','structure_ids','style_ids','tone_ids')})})
    common['_receipts']=array(obj({**strings('id','operation'),'output_refs':array(TEXT,1)}))
    layer=obj(strings('trigger','operation','result','verification'))
    network_layer=obj({'bindings':array(obj(strings('clause_id','trigger_ref','result_ref')),1)})
    clause=obj({**strings('id','reason','operation','observable','check'),
        'applicability':{'enum':['applies','not_applicable','source_unresolved']},
        'input_refs':array(TEXT),'output_refs':array(TEXT),
        'consumer':{'enum':['writer','review','acceptance',*ORDER]}})
    criterion=obj({'source_id':TEXT,'contract_sha256':TEXT,'clauses':array(clause),
                   'layer_application':{'anyOf':[layer,obj({})]}})
    common['_criteria']=array(criterion)
    if contracts is not None:
        from copy import deepcopy
        variants=[]
        for contract in contracts:
            variant=deepcopy(criterion);props=variant['properties']
            props['source_id']={'const':contract['source_id']};props['contract_sha256']={'const':contract['sha256']}
            ids=[r['id'] for r in contract['obligations']]
            if ids:props['clauses']['items']['properties']['id']={'enum':ids}
            props['clauses']['minItems']=len(ids);props['clauses']['maxItems']=len(ids)
            props['layer_application']=layer if contract.get('application_required') else obj({})
            if contract.get('network_layer_fields'):
                props['layer_application']=deepcopy(network_layer)
                if ids:
                    props['layer_application']['properties']['bindings']['items']['properties']['clause_id']={'enum':ids}
            variants.append(variant)
        common['_criteria']['maxItems']=len(variants)
        if variants:common['_criteria']['items']={'anyOf':variants}
    requirements=[r['id'] for r in (inputs or {}).get('static_relations',{}).get('products',{}).get('requirements',[])
                  if r['target_stage']==stage]
    common['_requirements']['maxItems']=len(requirements)
    if requirements:common['_requirements']['items']['properties']['id']={'enum':requirements}
    source_ids=[row['source']['id'] for row in sources]
    if source_ids:
        use['properties']['source_id']={'enum':source_ids}
        common['_excluded']['items']['properties']['source_id']={'enum':source_ids}
        common['_uses']['maxItems']=len(source_ids)
        common['_excluded']['maxItems']=len(source_ids)
    else:
        common['_uses']['maxItems']=0;common['_excluded']['maxItems']=0
    row=lambda *keys:obj(strings(*keys))
    member_kinds={'world_design':('world',),'character_design':('character',),
                  'plot_design':('plot','promise','volume','chapter'),'scene_design':('scene',)}
    shapes={
      'selection':array(row('id','label','basis')),'boundaries':array(TEXT), 'limitations':array(TEXT),'unknowns':array(TEXT),
      'concepts':array(obj({**strings('id','label','activation_basis'),'type_refs':array(TEXT,1)})),
      'adaptations':array(obj({'id':TEXT,'type_refs':array(TEXT,1),'parameters':state,'limits':array(TEXT)})),
      'focuses':array(row('id','concept','from_focus','to_focus','application')),
      'capabilities':array(obj({**strings('entity','basis'),'can_act':{'type':'boolean'},
                               'abilities':array(TEXT),'limits':array(TEXT)})),
      'states':array(obj({'entity':TEXT,'state':state,'status':{'const':'candidate'}})),
      'relations':array(row('id','source','target','relation','condition')),
      'requirements':array(obj({**strings('id','source_id','target_stage','constraint'),'project_refs':array(TEXT,1)})),
      'directions':array(obj(strings('title','conflict','consequence','reader_promise','protagonist_want',
                                   'resistance','choice','cost','ending_direction')),1),
      'reader_plan':array(obj({**strings('id','event','information','before_emotion','after_emotion','trigger','intended_effect','check'),
                              'order':{'type':'integer','minimum':1}})),
      'promise_plan':array(obj({**strings('id','promise','plant_event','setup','expected_meaning','payoff','check'),
          'payoff_event':{'type':['string','null']},'plant_chapter':{'type':'integer','minimum':1},
          'payoff_chapter':{'type':['integer','null'],'minimum':1},
          'payoff_window':{'anyOf':[{'type':'null'},obj({'min_offset':{'type':'integer','minimum':0},
              'max_offset':{'type':'integer','minimum':0}})]}})),
      'static_bindings':array(row('id','source_id','source','target','relation','condition')),
      'event_nodes':array(obj({**strings('id','goal','setting','obstacle','completion_condition'),
                              'actors':array(TEXT,1),'status':{'const':'planned'}})),
      'chapters':array(obj({'index':{'type':'integer','minimum':1},'card':{'type':['string','null']},
          'scenes':array(obj({'card':TEXT,'index':{'type':'integer','minimum':1},
                             'story_order':{'type':'integer'}}),1)}),1),
      'events':array(obj({**strings('id','scene','entity','trigger'),'before_state':state})),
      'selected_events':array(row('scene','event')),'selected_actions':array(row('scene','action')),
      'selected_propagations':array(row('scene','propagation')),
      'waiting':array(obj({**strings('source_id','reason'),'missing':array(TEXT,1)})),
      'patches':array(row('scene','choice','planned_result')),
      'transitions':array(obj({**strings('scene','entity','event','action','cost','failure','continuity'),
                               'before_state':state,'after_state':state})),
      'beats':array(obj({**strings('scene','observer','object','action','observable','check','action_ref','timing','trigger_basis'),
                        'step_index':{'type':'integer','minimum':0}},('action_ref','step_index','timing','trigger_basis')),1),
      'guidance':array(row('scene','observable','check'),1),
      'material_bindings':{'type':'object'},'process_bindings':{'type':'object'},
      'method_guidance':array(obj({**strings('scene','observable','check'),'source_ids':array(TEXT,1)})),
    }
    if stage == 'expression_design' and narration:
        from nw.materials.narration import ACCESS_POLICIES, MODES
        beat = obj({**strings('basis_ref','basis_quote','effect'), 'time': {'enum': ['current', 'past']},
                    'mode': {'enum': list(MODES)}, 'owner': {'type': ['string', 'null']}})
        if narration in ACCESS_POLICIES:
            beat['properties']['witnesses'] = array(TEXT)
            beat['required'].append('witnesses')
        shapes['guidance'] = array(obj({**strings('scene','observable','check'), 'narration': beat}), 1)
    if stage=='event_design':
        shapes['candidates']=array(obj({**strings('id','predecessor','event','completion_gate'),
            'source_ids':array(TEXT),'actors':array(TEXT,1),'status':{'const':'conditional_candidate'}}))
    elif stage=='action_design':
        shapes['candidates']=array(obj({**strings('id','event','actor','action','cost'),
            'source_ids':array(TEXT),'steps':array(row('object','action','obstacle','response','result'),1),
            'requires':array(TEXT,1),'limits':array(TEXT),'status':{'const':'candidate'}}))
    elif stage=='state_propagation':
        shapes['candidates']=array(obj({**strings('id','root_id','source_entity','target_entity',
            'external_action','continuity','activation_condition'),
            'root_kind':{'enum':['planned_change','accepted_fact']},'source_ids':array(TEXT),
            'gates':{'const':{'require_root_confirmation':True,'require_external_action_selection':True,
                              'require_continuity_validation':True}},
            'proposed_effect':state,'scene':{'type':['string','null']},'status':{'const':'conditional_candidate'}}))
    if stage in member_kinds:shapes['members']=array({'anyOf':[card(k,narration=narration) for k in member_kinds[stage]]})
    events=(inputs or {}).get('scene_design',{}).get('products',{}).get('events',[])
    if stage=='state_transition' and events:
        short={'type':'string','minLength':1,'maxLength':160}
        concise={'type':'string','minLength':1,'maxLength':80}
        scalar={'type':['string','number','boolean','null'],'maxLength':160}
        variants=[]
        for event in events:
            fields={key:short for key in ('action','cost','failure','continuity')}
            fields.update({key:concise for key in ('cost','failure','continuity')})
            fields.update({key:{'const':event[key]} for key in ('scene','entity')})
            fields.update(event={'const':event['id']},before_state={'const':event['before_state']},
                after_state={'type':'object','properties':{key:(scalar if not isinstance(value,(dict,list)) else ANY)
                    for key,value in event['before_state'].items()},'additionalProperties':False,'minProperties':1})
            variants.append(obj(fields))
        shapes['transitions']=array({'anyOf':variants})
        shapes['transitions']['maxItems']=len(events)
        shapes['patches']=array(obj({'scene':{'enum':list({e['scene'] for e in events})},'choice':short,'planned_result':short}))
        shapes['patches']['maxItems']=len({e['scene'] for e in events})
        use['properties']['output_refs']=array({'enum':['scene:'+scene for scene in sorted({e['scene'] for e in events})]},1)
    fields={key:shapes[key] for key in sorted(FIELDS[stage])};fields.update(common)
    craft_fields = {}
    if craft:
        from nw.materials.passage_craft import schema_fields
        craft_fields = schema_fields(stage,effect_kinds)
        fields.update(craft_fields)
    if passage and stage in ('scene_design', 'expression_design'):
        from nw.materials.passage_sequence import ROLES, STATUS, DETAIL
        optional_text = {'type': ['string', 'null']}
        if stage == 'scene_design':
            fields['passage_choices'] = array(obj({**strings('scene', 'event', 'need_quote', 'reason'),
                'kind': {'enum': [*ROLES, 'other']}, 'source_ref': optional_text,
                'fit': obj(strings('condition', 'boundary', 'prior_quote', 'boundary_check'))}, ('fit',)))
        else:
            step = obj({'beat': {'type': 'integer', 'minimum': 1}, 'focus_quote': TEXT,
                        'bridge_quote': optional_text, 'connection': optional_text,
                        'role': {'enum': sorted(set().union(*ROLES.values()))},
                        'detail': {'enum': list(DETAIL)}, 'status': {'enum': list(STATUS)}})
            number = {'type': 'integer', 'minimum': 1}
            comparison = obj({**strings('gate_quote', 'example_actor', 'example_choice', 'branch_actor', 'branch_choice'),
                              'example_beat': number, 'branch_beat': number})
            fields['passage_sequences'] = array(obj({'scene': TEXT, 'steps': array(step, 2), 'source_operation': TEXT,
                'source_beat': number, 'comparison': comparison}, ('source_operation', 'source_beat', 'comparison')))
    if cast_demand and stage == 'plot_design':
        fields['cast_events'] = array(obj(strings('demand', 'event')))
    if cast_demand and stage == 'scene_design':
        fields['cast_payoffs'] = array(obj({**strings('demand', 'scene', 'action'),
                                            'step_index': {'type': 'integer', 'minimum': 0}}))
    if cast_distribution and stage == 'scene_design':
        from nw.materials.cast_distribution_plan import schema as distribution_schema
        fields['cast_distribution_plan'] = distribution_schema()
    if stage == 'plot_design' and chapter_progress:
        fields['continuations'] = array(obj(strings('ref', 'event', 'target_quote', 'reason')))
    if stage == 'scene_design' and chapter_progress:
        from nw.materials.chapter_progress import CHANGES, CONNECTIONS, ORIGINS
        fields['scene_progress'] = array(obj({**strings('scene','basis_ref','basis_quote','stimulus'),
            'change': {'enum': list(CHANGES)}, 'origin': {'enum': list(ORIGINS)},
            'connection': {'enum': list(CONNECTIONS)}, 'next_pressure': {'type': ['string', 'null']}}), 1)
    if stage!='type_selection':fields.pop('_governance')
    if cast_demand:
        from nw.materials.cast_demands import add_schema
        add_schema(stage, fields)
    if stage=='plot_design':fields['static_bindings']=shapes['static_bindings']
    if stage == 'type_selection' and type_network_inputs:
        from nw.materials.type_network import INPUT_FIELDS

        names = tuple(sorted(INPUT_FIELDS))
        fields['adaptation_inputs'] = obj({name: obj(strings('ref', 'quote')) for name in names}, names)
    final=obj({'stage':{'const':stage},'products':obj(fields,('_excluded','_requirements','static_bindings','_governance',
                                                            '_receipts','adaptation_inputs','passage_choices','passage_sequences',*craft_fields))})
    if not allow_requests:return final
    actions=[obj({'action':{'const':'search'},'query':TEXT,'cursor':{'type':'integer','minimum':0}},('cursor',))]
    if readable:actions.append(obj({'action':{'const':'read'},'id':{'enum':list(readable)}}))
    request=obj({'stage':{'const':stage},'requests':array({'anyOf':actions},1)})
    return {'anyOf':[final,request]}
