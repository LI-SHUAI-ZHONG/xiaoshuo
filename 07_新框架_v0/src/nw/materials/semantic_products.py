"""Validate source-required project structures without scoring literary effects."""
import json
import re

from nw.task_models import _text,canonical


def require(ok: bool,reason: str) -> None:
    if not ok:raise ValueError('MATERIAL_SEMANTICS: '+reason)


def original(source: dict) -> object:
    raw=source.get('original_text','')
    try:return json.loads(raw)
    except (ValueError,TypeError):return raw


def source_text(source: dict) -> str:
    value=original(source)
    return value if isinstance(value,str) else canonical(value)


def domains(source: dict) -> set[str]:
    """These select artifact containers, never establish a semantic pass."""
    text=source_text(source);result=set()
    if any(word in text for word in ('读者情绪','读者情感')):result.add('reader')
    if '伏笔' in text and any(word in text for word in ('埋设','回收','揭示')):result.add('promise')
    return result


def _rows(value: object,fields: set[str],label: str) -> list[dict]:
    require(isinstance(value,list) and bool(value),label+' needs actual project rows')
    for row in value:
        require(isinstance(row,dict) and set(row)==fields,label+' has incomplete or invented fields')
    return value


def _reader(value: dict,sources: list[dict]) -> None:
    fields={'id','event','order','information','before_emotion','after_emotion','trigger','intended_effect','check'}
    rows=_rows(value['reader_plan'],fields,'reader plan')
    events={r['id'] for r in value['event_nodes']};seen=set();orders=set()
    for row in rows:
        require(all(_text(row[k]) for k in fields-{'order'}) and row['id'] not in seen
                and row['event'] in events and type(row['order']) is int and row['order']>0
                and row['order'] not in orders,'reader design needs actual information order, event and emotional trigger')
        seen.add(row['id']);orders.add(row['order'])
    require(orders==set(range(1,len(rows)+1)),'reader information order has gaps')
    wave=any(any(term in source_text(s) for term in ('不能是一条直线','必须有起有伏')) for s in sources)
    if wave:
        require(any(r['before_emotion']!=r['after_emotion'] for r in rows),
                'source requires an emotional change; a constant plan is not an instance')


def _promise_window(sources: list[dict]) -> tuple[int,int] | None:
    windows=[]
    for source in sources:
        text=source_text(source).replace('\\','')
        match=re.search(r'(?:首次引入|首次埋设).{0,12}?后[的\s]*(\d+)\s*[-–—~至到]\s*(\d+)\s*章',text)
        if match:windows.append((int(match[1]),int(match[2])))
    if not windows:return None
    require(len(set(windows))==1,'conflicting source payoff windows need an explicit ruling')
    return windows[0]


def _promise(value: dict,sources: list[dict],context: dict) -> None:
    fields={'id','promise','plant_event','payoff_event','plant_chapter','payoff_chapter','payoff_window',
            'setup','expected_meaning','payoff','check'}
    rows=_rows(value['promise_plan'],fields,'foreshadow plan')
    events={r['id'] for r in value['event_nodes']}
    promises={r['key']:r['body'] for r in value['members'] if r['kind']=='promise'}
    promises.update({r['card_id']:r['body'] for r in context.get('approved_cards',[]) if r['kind']=='promise'})
    seen=set();window=_promise_window(sources)
    for row in rows:
        require(all(_text(row[k]) for k in ('id','promise','plant_event','setup','expected_meaning','payoff','check'))
                and row['id'] not in seen and row['promise'] in promises and row['plant_event'] in events
                and (row['payoff_event'] is None or row['payoff_event'] in events)
                and type(row['plant_chapter']) is int and row['plant_chapter']>0,
                'foreshadow needs a real promise, plant event, meaning and return arrangement')
        seen.add(row['id'])
        require(all(canonical(row[k])==canonical(promises[row['promise']][k]) for k in ('setup','payoff')),
                'foreshadow plan differs from its actual promise artifact')
        limits=row['payoff_window']
        require(limits is None or isinstance(limits,dict) and set(limits)=={'min_offset','max_offset'}
                and all(type(v) is int and v>=0 for v in limits.values())
                and limits['min_offset']<=limits['max_offset'],'payoff window must be explicit or unknown')
        if window:
            require(limits=={'min_offset':window[0],'max_offset':window[1]},
                    'payoff window does not preserve the actual source interval')
        if row['payoff_chapter'] is not None:
            require(type(row['payoff_chapter']) is int and row['payoff_chapter']>=row['plant_chapter'],
                    'payoff chapter precedes the plant')
            if limits:
                require(limits['min_offset']<=row['payoff_chapter']-row['plant_chapter']<=limits['max_offset'],
                        'payoff chapter is outside the source/project window')


def validate_plot_products(value: dict,sources: list[dict],context: dict) -> None:
    used={r['source_id'] for r in value.get('_uses',[])}
    reader=[s for s in sources if s['source']['id'] in used and 'reader' in domains(s)]
    promise=[s for s in sources if s['source']['id'] in used and 'promise' in domains(s)]
    if reader:_reader(value,reader)
    if promise:_promise(value,promise,context)


def _product(products: dict,stage: str) -> dict:
    return products.get(stage,{}).get('products',{})


def _relation_uses(products: dict,source_id: str) -> list[dict]:
    result=[]
    for stage,field in (('static_relations','relations'),('plot_design','static_bindings')):
        product=_product(products,stage)
        refs={ref for use in product.get('_uses',[]) if use['source_id']==source_id for ref in use['output_refs']}
        result.extend(r for r in product.get(field,[]) if r.get('source_id')==source_id or 'relation:'+r['id'] in refs)
    return result


def validate_static_bindings(value: dict,products: dict,sources: list[dict],context: dict) -> None:
    rows=value.get('static_bindings',[])
    require(isinstance(rows,list),'plot static bindings must be an explicit list')
    pool={s['source']['id']:s for s in [*context.get('method_sources',[]),*sources]}
    endpoints={r['card_id'] for r in context.get('approved_cards',[])}
    for stage in ('world_design','character_design'):
        endpoints.update(r['key'] for r in _product(products,stage).get('members',[]))
    endpoints.update(r['key'] for r in value.get('members',[]))
    used={r['source_id'] for r in value.get('_uses',[])};seen=set()
    for row in rows:
        require(isinstance(row,dict) and set(row)=={'id','source_id','source','target','relation','condition'}
                and all(_text(v) for v in row.values()) and row['id'] not in seen
                and row['source'] in endpoints and row['target'] in endpoints,
                'post-plot relationship needs existing project endpoints and a unique identity')
        seen.add(row['id']);item=pool.get(row['source_id'])
        raw=original(item) if item else None
        require(row['source_id'] in used and isinstance(raw,dict)
                and all(raw.get(k) for k in ('source','target','type'))
                and not raw.get('generated_from_static') and not raw.get('effect'),
                'post-plot relationship must instantiate a read static method at this step')


def adopted_relation(source: dict,products: dict,context: dict) -> list[dict]:
    raw=original(source)
    if not isinstance(raw,dict) or not raw.get('generated_from_static'):return []
    signature=tuple(raw.get(k) for k in ('source','target','type'))
    sources={s['source']['id']:s for s in context.get('method_sources',[])}
    matches=[]
    for ident,item in sources.items():
        candidate=original(item)
        if isinstance(candidate,dict) and not candidate.get('generated_from_static') and not candidate.get('effect'):
            if tuple(candidate.get(k) for k in ('source','target','type'))==signature:
                matches.extend(_relation_uses(products,ident))
    return matches


def validate_dynamic_dependencies(stage: str,value: dict,products: dict,sources: list[dict],context: dict) -> None:
    used={r['source_id'] for r in value.get('_uses',[])}
    for item in sources:
        raw=original(item)
        if item['source']['id'] not in used or not isinstance(raw,dict) or not raw.get('generated_from_static'):continue
        relations=adopted_relation(item,products,context)
        require(bool(relations),'dynamic source has no actual adopted static relationship')
        if stage=='state_propagation':
            own=[r for r in value['candidates'] if item['source']['id'] in r['source_ids']]
            require(bool(own) and all(any(r['source_entity']==s['source'] and r['target_entity']==s['target']
                    for s in relations) for r in own),'dynamic candidate differs from adopted static project endpoints')


def validate_anchor_products(value: dict,products: dict,sources: list[dict]) -> None:
    used={r['source_id'] for r in value.get('_uses',[])}
    anchors=[s for s in sources if s['source']['id'] in used and s['source'].get('profile')=='anchor']
    if not anchors:return
    chosen={r['scene']:r['action'] for r in _product(products,'scene_design').get('selected_actions',[])}
    actions={r['id']:r for r in _product(products,'action_design').get('candidates',[])}
    for row in value['beats']:
        require(row.get('action_ref')==chosen.get(row['scene']) and row.get('action_ref') in actions,
                'anchor has no actual selected upstream action')
        action=actions[row['action_ref']]
        require(type(row.get('step_index')) is int and 0<=row['step_index']<len(action['steps'])
                and row.get('timing') in ('before','during','after') and _text(row.get('trigger_basis')),
                'anchor needs an actual action beat, timing and source-condition basis')
