"""Derived methods keep exact approved-structure provenance through revisions."""
import json
from uuid import uuid4

from nw.studio.catalog import canonical_types
from nw.studio.corpus_catalog import require_current_schema
from nw.studio.corpus_passages import method_sequence
from nw.studio.library_util import encode, timestamp
from nw.studio.method_contract import draft
from nw.studio.method_catalog import TASKS
from nw.studio.method_evidence import resolve
from nw.studio.method_store import digest
from nw.studio.corpus_story_observations import STORY_TASKS, story_observation_issue

TASK_FOR_DOMAIN={'main_plot':'main_plot','subplot':'subplot','character_arc':'character_arc',
    'hook':'hook','foreshadow':'foreshadow','information':'information','pacing':'pacing','world_rules':'world_rules',
    'narration':'narration', **{domain:tasks[0] for domain,tasks in STORY_TASKS.items()}}


def check_story_method(service: object, structure: dict, body: dict, basis: dict) -> None:
    document=structure['body']
    threads=[t for t in document['threads'] if t['id'] in basis['thread_ids'] and t['domain'] in STORY_TASKS]
    if not threads:
        return
    check_source_types(service,structure,body)
    quotes={(e['start'],e['end'],e['quote']) for e in body['evidence'] if e['book_id']==structure['book_id']}
    evidence={e['id']:e for e in document['evidence'] if (e['start'],e['end'],e['quote']) in quotes}
    events={e['id']:e for e in document['events'] if e['id'] in basis['event_ids']}
    links=[l for l in document['links'] if l['id'] in basis['link_ids']]
    units={u['id']:u for u in document['units']}
    characters={p['id']:p for p in document['characters']}
    observed={d['domain'] for d in document['domains'] if d['status']=='observed'}
    source_ids={key for t in document['threads'] if t['id'] in basis['thread_ids'] for key in t['evidence_ids']}
    source_ids.update(key for row in [*events.values(),*links] for key in row['evidence_ids'])
    if not evidence.keys() <= source_ids:
        raise ValueError('章场方法引文不属于所选观察、事件或关系')
    for thread in threads:
        domain=thread['domain']
        if thread['status']=='uncertain' or domain not in observed:
            raise ValueError('章场方法不能来自未核实的观察')
        target_tasks=set(body['tasks']).intersection(STORY_TASKS[domain])
        if not target_tasks:
            raise ValueError('章场方法的生产任务与所选章场推进或人物出场观察不符')
        selection={**thread,'node_ids':[node for node in thread['node_ids'] if node in events],
                   'evidence_ids':list(evidence.keys() & set(thread['evidence_ids']))}
        if domain=='cast_roster':
            detail=thread['details']
            if (not selection['node_ids'] or detail['appearance_evidence'] not in selection['evidence_ids']
                    or (detail['standing_evidence'] and detail['standing_evidence'] not in selection['evidence_ids'])):
                raise ValueError('阵容方法须引用本人物的原事件、实际出场或提及依据及所采用的地位凭据')
        issue=story_observation_issue(selection,events,links,units,evidence,characters)
        if issue:
            raise ValueError(issue)
        stages={stage for task in target_tasks for stage in TASKS[task]['stages']}
        targets={'members','event_nodes','reader_plan','promise_plan','candidates','events','chapters',
                 'guidance','patches','transitions'}
        targets.update({'cast_assignments','cast_events','cast_payoffs'} if domain in ('cast_entry','cast_roster')
                       else {'continuations','scene_progress'})
        if not any(o['stage'] in stages and o['field'] in targets and
                   (o['field']!='members' or o['artifact_kind']!='stage_product') for o in body['outputs']):
            raise ValueError('章场方法须落到可交接的本项目设计卡、事件、信息或状态产物')


def check_source_types(service: object, structure: dict, body: dict) -> None:
    confirmed=json.loads(service._staging_row(structure['book_id'])['confirmed_types_json'])
    tags={tag for value in confirmed for tag in canonical_types([value])}
    if not set(body['type_tags'])<=tags:
        raise ValueError('方法的适用类型超出参考作品已确认类型')


def check_narration_method(service: object, structure: dict, body: dict, basis: dict) -> None:
    document=structure['body']
    threads=[t for t in document['threads'] if t['id'] in basis['thread_ids'] and t['domain']=='narration']
    if not threads and 'narration' not in body['tasks']:
        return
    if not threads or 'narration' not in body['tasks'] or not any(
            d['domain']=='narration' and d['status']=='observed' for d in document['domains']):
        raise ValueError('叙述方法须使用已核实的叙述观察和叙述制作任务')
    check_source_types(service,structure,body)
    quoted={(e['start'],e['end'],e['quote']) for e in body['evidence'] if e['book_id']==structure['book_id']}
    cited={e['id'] for e in document['evidence'] if (e['start'],e['end'],e['quote']) in quoted}
    events={e['id']:set(e['evidence_ids']) for e in document['events'] if e['id'] in basis['event_ids']}
    related={eid for field,section in [('thread_ids','threads'),('event_ids','events'),('link_ids','links')]
             for row in document[section] if row['id'] in basis[field] for eid in row['evidence_ids']}
    if not quoted<={(e['start'],e['end'],e['quote']) for e in document['evidence'] if e['id'] in related}:
        raise ValueError('叙述方法不可借用所选叙述观察、事件与关系以外的引文')
    for thread in threads:
        nodes=events.keys() & set(thread['node_ids'])
        if thread['status']=='uncertain' or not nodes or any(
                not cited.intersection(events[node],thread['evidence_ids']) for node in nodes):
            raise ValueError('叙述方法须引用所选叙述观察及各实际事件的原文短引')
        sequence=thread['details'].get('passage_sequence')
        if sequence:
            beats=sequence['beats']
            if any(b['event_id'] not in nodes or b['evidence_id'] not in cited for b in beats):
                raise ValueError('连续段落方法须引用每个落点的细拆事件及该处原句，不能跳过中间的承接')
            grounded={b['role'] for b in beats if b['claim_status'] in ('stated','attributed')}
            if any(b['role']!='handoff' and b['role'] not in grounded for b in beats):
                raise ValueError('手法的关键承接只凭推测或未知，须补原文叙述或可归属的言行后再提炼')


def check_world_method(service: object, structure: dict, body: dict, basis: dict) -> None:
    document=structure['body']
    threads=[t for t in document['threads'] if t['id'] in basis['thread_ids'] and t['domain']=='world_rules']
    if not threads:
        raise ValueError('世界方法须来自已核实的世界规则线索，请先从原作拆解规则和受影响的事件')
    check_source_types(service,structure,body)
    quotes={(e['start'],e['end'],e['quote']) for e in body['evidence'] if e['book_id']==structure['book_id']}
    cited={e['id'] for e in document['evidence'] if (e['start'],e['end'],e['quote']) in quotes}
    events={e['id']:e for e in document['events'] if e['id'] in basis['event_ids']}
    links=[link for link in document['links'] if link['id'] in basis['link_ids']]
    basis_evidence={i for row in [*events.values(),*links,*[t for t in document['threads'] if t['id'] in basis['thread_ids']]]
                    for i in row['evidence_ids']}
    if not quotes<={(e['start'],e['end'],e['quote']) for e in document['evidence'] if e['id'] in basis_evidence}:
        raise ValueError('世界方法引文须属于所选线索、事件或关系的证据')
    causal_links=[link for link in links if link['kind'] in ('causes','enables','opposes')]
    observed={row['domain'] for row in document['domains'] if row['status']=='observed'}
    if 'world_rules' not in observed:
        raise ValueError('原作的世界规则尚待核实，不能提炼为可采用的方法')
    for thread in threads:
        if thread['status']=='uncertain' or not all(thread['details'].values()) or not cited.intersection(thread['evidence_ids']):
            raise ValueError('须提供原作规则、条件、局限与实际后果及可定位的规则证据')
        nodes=set(thread['node_ids']) & events.keys()
        consequences={i for i in nodes if events[i]['result'] and cited.intersection(events[i]['evidence_ids'])}
        if len(nodes)==1 and any(cited.intersection(thread['evidence_ids'],events[i]['evidence_ids']) for i in consequences):
            continue
        if not any(link['thread_id']==thread['id'] and link['source'] in nodes and link['target'] in consequences
                   and cited.intersection(events[link['source']]['evidence_ids']) for link in causal_links):
            raise ValueError('世界方法须引用受规则影响的实际事件与结果，跨事件须有因果或约束关系及两端证据')
    output_keys={out['key'] for out in body['outputs'] if (out['stage'],out['field'],out['artifact_kind'])
                 ==('world_design','members','world')}
    if not any(row['output_key'] in output_keys and row['consumer'] in
               ('character_design','static_relations','plot_design','event_design','action_design','scene_design')
               for row in body['downstream']):
        raise ValueError('世界方法须生成本项目世界卡，并说明人物、关系、剧情、事件、行动或场景步骤如何使用')
    if not any(row['input_kind'] in ('brief','type_selection','type_adaptation','parent_outline','accepted_state')
               for row in body['prerequisites']):
        raise ValueError('世界方法须明确所需的本项目立项、类型、上层设计或已接受状态前置')


def origin_status(service: object, method_id: str, version: int, body: dict, conn: object) -> tuple[dict | None,list[dict],int | None]:
    row=conn.execute('SELECT * FROM corpus_method_origins WHERE method_id=? AND method_version=?',(method_id,version)).fetchone()
    if not row:return None,[],None
    origin=dict(row);origin['basis']=json.loads(origin.pop('basis_json'));issues=[]
    source_schema=None
    try:
        structure=service._corpus_row(origin['book_id'],origin['structure_version'],conn)
        source_schema=structure['body'].get('schema_version',1)
        if structure['approved_version']!=origin['structure_version'] or not structure['available']:
            raise ValueError('参考结构已更新、未批准或来源失效；此方法须依据当前结构重新提炼')
        expected={(e['start'],e['end'],e['quote']) for e in structure['body']['evidence']}
        if any(e['book_id']!=origin['book_id'] or (e['start'],e['end'],e['quote']) not in expected for e in body['evidence']):
            raise ValueError('方法证据不在其冻结的结构版本内')
        if structure['body']['source_extent']['status']!='complete' and set(body['scopes'])&{'book','volume'}:
            raise ValueError('不完整或未确认完整性的文本，不能支撑全书/整卷方法结论')
        if structure['body'].get('schema_version',1)>=2 and 'world_rules' in body['tasks']:
            check_world_method(service,structure,body,origin['basis'])
        check_narration_method(service,structure,body,origin['basis'])
        check_story_method(service,structure,body,origin['basis'])
        story_domains=sorted({t['domain'] for t in structure['body']['threads']
                              if t['id'] in origin['basis']['thread_ids'] and t['domain'] in STORY_TASKS})
        if story_domains:
            origin['observation_domains']=story_domains
        passages=[method_sequence(t) for t in structure['body']['threads'] if t['id'] in origin['basis']['thread_ids']
                  and t['domain']=='narration' and 'passage_sequence' in t['details']]
        if passages:
            origin['passage_sequences']=passages
        origin['source_extent']=structure['body']['source_extent']
    except (OSError,ValueError,KeyError) as exc:
        issues=[{'field':'origin','message':str(exc)}]
    return origin,issues,source_schema


def inherit_origin(conn: object, method_id: str, previous: int, version: int) -> None:
    row=conn.execute('SELECT * FROM corpus_method_origins WHERE method_id=? AND method_version=?',(method_id,previous)).fetchone()
    if row:conn.execute('INSERT INTO corpus_method_origins VALUES(?,?,?,?,?,?)',
        (method_id,version,row['book_id'],row['structure_version'],row['basis_json'],timestamp()))


def prepare_method(service: object, structure: dict, candidate: dict, *, complete: bool = True) -> dict:
    if not isinstance(candidate,dict) or set(candidate)!={'body','basis'}:raise ValueError('提炼方法必须包含方法正文和明确结构依据')
    basis=candidate['basis']
    if not isinstance(basis,dict) or set(basis)!={'thread_ids','event_ids','link_ids','explanation'}:
        raise ValueError('方法依据须指定线索/弧光、事件、关系及解释')
    document=structure['body']
    for name,section in (('thread_ids','threads'),('event_ids','events'),('link_ids','links')):
        ids={r['id'] for r in document[section]};values=basis[name]
        if not isinstance(values,list) or any(v not in ids for v in values) or len(set(values))!=len(values):
            raise ValueError('方法依据引用了不存在或重复的结构节点')
    if not basis['thread_ids'] or not basis['event_ids'] or not isinstance(basis['explanation'],str) or not basis['explanation'].strip():
        raise ValueError('方法必须说明依据哪些实际线索/事件及为什么可迁移')
    selected=[t for t in document['threads'] if t['id'] in basis['thread_ids']]
    if not set(basis['event_ids'])<=set().union(*(set(t['node_ids']) for t in selected)):
        raise ValueError('方法事件不属于所选线索/弧光')
    selected_links=[l for l in document['links'] if l['id'] in basis['link_ids']]
    if any(l['source'] not in basis['event_ids'] or l['target'] not in basis['event_ids'] or
           l['thread_id'] is not None and l['thread_id'] not in basis['thread_ids'] for l in selected_links):
        raise ValueError('方法关系必须对应所选线索及实际事件')
    body,issues=draft(candidate['body'])
    if complete and issues:raise ValueError('提炼的方法尚不完整：'+'；'.join(i['message'] for i in issues[:8]))
    related_ids={k for row in [*selected,*selected_links,*[e for e in document['events'] if e['id'] in basis['event_ids']]]
                 for k in row['evidence_ids']}
    evidence={(e['start'],e['end'],e['quote']) for e in document['evidence'] if e['id'] in related_ids}
    if any(e['book_id']!=structure['book_id'] or (e['start'],e['end'],e['quote']) not in evidence for e in body['evidence']):
        raise ValueError('方法必须引用当前已批准结构中的真实证据')
    if document['source_extent']['status']!='complete' and set(body['scopes'])&{'book','volume'}:
        raise ValueError('摘录或完整性未知时不能提炼全书/整卷方法')
    if complete and 'world_rules' in body['tasks']:
        check_world_method(service,structure,body,basis)
    if complete:
        check_narration_method(service,structure,body,basis)
        check_story_method(service,structure,body,basis)
    if len(encode(body).encode('utf-8'))>96*1024:raise ValueError('提炼方法超过96KiB，请分用途提炼')
    pins,errors=resolve(service,body['evidence'])
    if errors:raise ValueError('；'.join(i['message'] for i in errors))
    return {'body':body,'basis':basis,'pins':pins}


def publish_methods(service: object, conn: object, book_id: str, version: int, candidates: list[dict], *, complete: bool = True) -> list[dict]:
    structure=service._corpus_row(book_id,version,conn)
    if not structure['available'] or structure['approved_version']!=version:raise ValueError('须使用当前已批准且来源有效的结构版本')
    prepared=[prepare_method(service,structure,candidate,complete=complete) for candidate in candidates]
    results=[]
    for method in prepared:
        body,basis,pins=method['body'],method['basis'],method['pins']
        existing=conn.execute('SELECT o.method_id,o.method_version FROM corpus_method_origins o '
            'JOIN production_method_versions v ON v.method_id=o.method_id AND v.version=o.method_version '
            'WHERE o.book_id=? AND o.structure_version=? AND v.body_sha256=? AND o.basis_json=?',
            (book_id,version,digest(body),encode(basis))).fetchone()
        if existing:results.append({'id':existing['method_id'],'version':existing['method_version'],'duplicate':True});continue
        ident,now=uuid4().hex,timestamp()
        conn.execute('INSERT INTO production_methods VALUES(?,1,NULL,NULL,?,?)',(ident,now,now))
        conn.execute('INSERT INTO production_method_versions VALUES(?,1,?,?,?,?,?)',
                     (ident,encode(body),digest(body),encode(pins),'{}',now))
        conn.execute('INSERT INTO corpus_method_origins VALUES(?,1,?,?,?,?)',(ident,book_id,version,encode(basis),now))
        results.append({'id':ident,'version':1,'duplicate':False})
    return results


def manual_method(service: object, book_id: str, request: dict) -> dict:
    version=request.get('version');thread_ids=request.get('thread_ids',[])
    structure=service.get_corpus(book_id,version)
    require_current_schema(structure['body'].get('schema_version', 1))
    threads=[t for t in structure['body']['threads'] if t['id'] in thread_ids]
    if not threads or len(threads)!=len(set(thread_ids)):raise ValueError('请选择实际线索/弧光作为手工提炼依据')
    evidence_ids=set().union(*(set(t['evidence_ids']) for t in threads))
    events=set().union(*(set(t['node_ids']) for t in threads))
    links=[l['id'] for l in structure['body']['links'] if l['thread_id'] in thread_ids]
    body={'title':threads[0]['title'][:120], 'tasks':list(dict.fromkeys(TASK_FOR_DOMAIN[t['domain']] for t in threads)),
          'scopes':[],'type_tags':json.loads(service._staging_row(book_id)['confirmed_types_json']),
          'evidence':[{'book_id':book_id,**{k:e[k] for k in ('start','end','quote','explanation')}}
                      for e in structure['body']['evidence'] if e['id'] in evidence_ids]}
    candidate={'body':body,'basis':{'thread_ids':thread_ids,'event_ids':sorted(events),'link_ids':links,
                                  'explanation':'作者从所选已批准结构建立待补齐的方法草稿；尚未归纳具体操作。'}}
    with service.connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        result=publish_methods(service,conn,book_id,version,[candidate],complete=False)[0]
    return service.get_method(result['id'])
