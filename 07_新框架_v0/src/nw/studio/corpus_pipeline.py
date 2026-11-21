"""Read the whole source, integrate globally, refine, reconcile, then derive."""
from copy import deepcopy
import json

from nw.studio.corpus_calls import PipelineStop, check_control, model_call
from nw.studio.corpus_catalog import domains_for
from nw.studio.corpus_context import choose_window, relation_events, window_payload
from nw.studio.corpus_contract import normalize_document
from nw.studio.corpus_merge import merge_fragment, resolve_fragment
from nw.studio.corpus_methods import prepare_method, publish_methods
from nw.studio.corpus_prompts import messages, method_messages
from nw.studio.corpus_store import body_hash
from nw.studio.corpus_story_observations import STORY_TASKS
from nw.studio.library_util import encode, timestamp


def save_state(service: object, job_id: str, state: dict, phase: str) -> None:
    with service.connect() as conn:
        changed=conn.execute("UPDATE corpus_jobs SET state_json=?,phase=?,updated_at=? WHERE id=? AND status='running'",
                             (encode(state),phase,timestamp(),job_id)).rowcount
    if not changed:raise PipelineStop('任务已停止','cancelled')


def do_read(service: object, job: dict, state: dict, config: object, provider: object, content: str, phase: str) -> None:
    cursor_key='survey_cursor' if phase=='survey' else 'detail_cursor'
    while state[cursor_key]<len(state['spans']):
        index=state[cursor_key];span=state['spans'][index];doc=state['document'];prefix=('M' if phase=='survey' else 'D')+f'{index+1:05}'
        unit=next(u for u in doc['units'] if u['id']==span['unit_id'])
        payload={'prefix':prefix,'unit':unit,'span':span,'source_extent':doc['source_extent'],
                 'source_text':content[span['start']:span['end']],
                 'known_characters':[{'id':p['id'],'name':p['name'],'canonical_id':p['canonical_id']} for p in doc['characters']]}
        if phase=='detail':
            basis=state['global_basis'];coarse=[e for e in doc['events'] if e['unit_id']==unit['id'] and e['granularity']=='overview']
            ids={e['id'] for e in coarse}
            payload.update(global_overview=basis['overview'],global_basis_sha256=basis['sha256'],
                relevant_threads=[t for t in basis['threads'] if t['domain']=='main_plot' or set(t['node_ids'])&ids],
                overview_events=coarse,previous_scenes=[u for u in doc['units'] if u['level']=='scene' and u['parent_id']==unit['id']])
        def validator(raw: dict) -> dict:
            return resolve_fragment(raw,doc,content,span=span,prefix=prefix,phase=phase)
        patch,seq=model_call(service,job['id'],config,provider,key=f'{phase}:{index}',phase=phase,
                             messages=messages(phase,payload,version=doc['schema_version']),validator=validator)
        state['document']=merge_fragment(doc,patch)
        state['coverage']['survey_ranges' if phase=='survey' else 'detail_ranges'].append({**span,'call_seq':seq})
        state[cursor_key]+=1;save_state(service,job['id'],state,phase)


def do_windows(service: object, job: dict, state: dict, config: object, provider: object, content: str,
               phase: str, domain: str | None = None) -> None:
    cursor_key='overview_cursor' if phase=='overview' else 'relation_cursor'
    doc=state['document']
    events=[e for e in doc['events'] if e['granularity']=='overview'] if phase=='overview' else relation_events(doc)
    if not events:raise ValueError('原文没有可核对的事件观察；请先手工补充或核对来源，不能累加空条目')
    while state[cursor_key]<len(events):
        cursor=state[cursor_key];doc=state['document'];prefix=('G' if phase=='overview' else 'R_'+str(state['domain_index']))+f'_{cursor:05}'
        key=f'{phase}:{domain or "global"}:{cursor}'
        pending=state.get('pending_window')
        if pending and pending['key']!=key:raise ValueError('恢复窗口与持久检查点不一致')
        if pending:ids,next_cursor=pending['ids'],pending['next_cursor']
        else:
            ids,next_cursor=choose_window(doc,events,cursor,phase=phase,domain=domain,prefix=prefix,
                maximum=job['options']['max_input_chars'],global_basis=state.get('global_basis'))
            state['pending_window']={'key':key,'ids':ids,'next_cursor':next_cursor}
            save_state(service,job['id'],state,phase)
        selected=[e for e in events if e['id'] in ids]
        last=next_cursor==len(events)
        payload=window_payload(doc,selected,domain=domain,prefix=prefix,last=last,global_basis=state.get('global_basis'))
        allowed_events={e['id'] for e in [*payload['events'],*payload['frontier_events']]}
        allowed_evidence={e['id'] for e in payload['evidence']}
        def validator(raw: dict) -> dict:
            patch=resolve_fragment(raw,doc,content,span=None,prefix=prefix,phase=phase,domain=domain,
                                   event_allowlist=allowed_events,evidence_allowlist=allowed_evidence)
            if phase=='relations' and last and not any(d.get('domain')==domain for d in patch.get('domains',[])):
                raise ValueError('该职责已遍历全部事件，必须说明已观察/未观察/存疑及依据')
            if domain=='cast_roster':
                from nw.studio.corpus_roster import canonical_person
                people={p['id']:p for p in doc['characters']}
                required={(e['id'],canonical_person(p,people)) for e in selected
                          if e['granularity']=='detail' for p in e['characters']}
                seen={(t['node_ids'][0],canonical_person(t['characters'][0],people))
                      for t in [*doc['threads'],*patch.get('threads',[])] if t['domain']=='cast_roster'}
                if required-seen:
                    raise ValueError('本章阵容窗口仍有未核对的实际事件人物；须逐人登记，依据不足可标存疑')
            if phase=='overview' and last:
                integrated=merge_fragment(doc,patch)
                if not all(integrated['overview'].values()) or not integrated['threads']:
                    raise ValueError('必须先形成有来源节点的全局结构和覆盖限制，再进入章场细拆')
            return patch
        patch,_=model_call(service,job['id'],config,provider,key=key,phase=phase,
                           messages=messages(phase,payload,version=doc['schema_version']),validator=validator)
        state['document']=merge_fragment(doc,patch);state[cursor_key]=next_cursor;state.pop('pending_window',None)
        save_state(service,job['id'],state,phase)


def derive_methods(service: object, job: dict, state: dict, config: object, provider: object) -> None:
    selected=job['options']['thread_ids'];structure=service.get_corpus(job['book_id'],job['base_version'])
    if not structure['available'] or structure['approved_version']!=job['base_version']:raise ValueError('已批准结构改变，请重新选择')
    doc=structure['body'];threads={t['id']:t for t in doc['threads']}
    while state['method_cursor']<len(selected):
        index=state['method_cursor'];thread=threads[selected[index]]
        events=[e for e in doc['events'] if e['id'] in thread['node_ids']]
        links=[l for l in doc['links'] if l['thread_id']==thread['id']]
        eids=set(thread['evidence_ids'])|{k for e in events for k in e['evidence_ids']}|{k for l in links for k in l['evidence_ids']}
        payload={'book_id':job['book_id'],'structure_version':structure['version'],'structure_sha256':structure['body_sha256'],
            'source_extent':doc['source_extent'],'overview':doc['overview'],'thread':thread,'events':events,'links':links,
            'evidence':[{'book_id':job['book_id'],**e} for e in doc['evidence'] if e['id'] in eids],
            'confirmed_types':json.loads(service._staging_row(job['book_id'])['confirmed_types_json'])}
        if thread['domain'] in STORY_TASKS:
            people=set(thread['characters'])|{who for event in events for who in event['characters']}
            payload['participants']=[{'id':p['id'],'name':p['name']} for p in doc['characters'] if p['id'] in people]
        def validator(raw: dict) -> list:
            if not isinstance(raw,dict) or set(raw)!={'methods'} or not isinstance(raw['methods'],list) or len(raw['methods'])>3:
                raise ValueError('每条线索每次只能返回0–3个有明确依据的方法')
            for candidate in raw['methods']:
                if set(candidate.get('basis',{}).get('thread_ids',[]))!={thread['id']}:raise ValueError('方法须依据当前选定线索')
                if thread['domain']=='world_rules' and 'world_rules' not in candidate.get('body',{}).get('tasks',[]):
                    raise ValueError('世界规则线索只能提炼有世界设计用途的方法，缺乏依据可返回空列表')
                prepare_method(service,structure,candidate)
            return raw['methods']
        candidates,_=model_call(service,job['id'],config,provider,key=f'methods:{index}',phase='methods',
                                messages=method_messages(payload,version=doc['schema_version']),validator=validator)
        state['candidates'].extend(candidates);state['method_cursor']+=1
        save_state(service,job['id'],state,'methods')


def publish(service: object, job: dict, state: dict, content: str) -> None:
    check_control(service,job['id'])
    with service.connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        current=conn.execute('SELECT status,control FROM corpus_jobs WHERE id=?',(job['id'],)).fetchone()
        if current['status']!='running' or current['control']:raise PipelineStop('任务已停止，未发布新结果')
        if job['kind']=='structure':
            body=normalize_document(state['document'],content)
            state['published_version']=service._store_corpus(conn,job['book_id'],body,job['base_version'],state['coverage'],job_id=job['id'])
            target='archived' if job['original_book_status']=='archived' else 'pending_verify'
        else:
            state['published_methods']=publish_methods(service,conn,job['book_id'],job['base_version'],state['candidates'])
            target=job['original_book_status']
        conn.execute("UPDATE corpus_jobs SET status='completed',phase='publish',state_json=?,error='',updated_at=? WHERE id=?",
                     (encode(state),timestamp(),job['id']))
        conn.execute("UPDATE staging_books SET status=?,progress=1,error='',updated_at=? WHERE id=? AND status='decomposing'",(target,timestamp(),job['book_id']))


def run_job(service: object, job_id: str, config: object, provider: object) -> None:
    with service.connect() as conn:raw=conn.execute('SELECT * FROM corpus_jobs WHERE id=?',(job_id,)).fetchone()
    job=dict(raw);job['options']=json.loads(job['options_json']);state=json.loads(job['state_json'])
    try:
        content=service._book_text(service._staging_row(job['book_id']))
        if job['kind']=='methods':derive_methods(service,job,state,config,provider)
        else:
            do_read(service,job,state,config,provider,content,'survey')
            do_windows(service,job,state,config,provider,content,'overview')
            if 'global_basis' not in state:
                state['global_basis']={'overview':deepcopy(state['document']['overview']),
                    'threads':deepcopy(state['document']['threads']),'sha256':body_hash(state['document'])}
                save_state(service,job_id,state,'detail')
            do_read(service,job,state,config,provider,content,'detail')
            domains=list(domains_for(state['document']['schema_version']))
            while state['domain_index']<len(domains):
                domain=domains[state['domain_index']]
                do_windows(service,job,state,config,provider,content,'relations',domain)
                state['domain_index']+=1;state['relation_cursor']=0;save_state(service,job_id,state,'relations')
        publish(service,job,state,content)
    except Exception as exc:
        status=exc.status if isinstance(exc,PipelineStop) else 'failed'
        with service.connect() as conn:
            conn.execute("UPDATE corpus_jobs SET status=?,error=?,control='',updated_at=? WHERE id=? AND status NOT IN ('completed','cancelled')",
                         (status,str(exc)[:4000],timestamp(),job_id))
            conn.execute("UPDATE staging_books SET status=?,error=?,updated_at=? WHERE id=? AND status='decomposing'",
                         (job['original_book_status'],str(exc)[:4000],timestamp(),job['book_id']))
