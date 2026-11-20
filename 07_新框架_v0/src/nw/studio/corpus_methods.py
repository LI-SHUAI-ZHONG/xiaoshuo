"""Derived methods keep exact approved-structure provenance through revisions."""
import json
from uuid import uuid4

from nw.studio.library_util import encode, timestamp
from nw.studio.method_contract import draft
from nw.studio.method_evidence import resolve
from nw.studio.method_store import digest

TASK_FOR_DOMAIN={'main_plot':'main_plot','subplot':'subplot','character_arc':'character_arc',
    'hook':'hook','foreshadow':'foreshadow','information':'information','pacing':'pacing'}


def origin_status(service: object, method_id: str, version: int, body: dict, conn: object) -> tuple[dict | None,list[dict]]:
    row=conn.execute('SELECT * FROM corpus_method_origins WHERE method_id=? AND method_version=?',(method_id,version)).fetchone()
    if not row:return None,[]
    origin=dict(row);origin['basis']=json.loads(origin.pop('basis_json'));issues=[]
    try:
        structure=service._corpus_row(origin['book_id'],origin['structure_version'],conn)
        if structure['approved_version']!=origin['structure_version'] or not structure['available']:
            raise ValueError('参考结构已更新、未批准或来源失效；此方法须依据当前结构重新提炼')
        expected={(e['start'],e['end'],e['quote']) for e in structure['body']['evidence']}
        if any(e['book_id']!=origin['book_id'] or (e['start'],e['end'],e['quote']) not in expected for e in body['evidence']):
            raise ValueError('方法证据不在其冻结的结构版本内')
        if structure['body']['source_extent']['status']!='complete' and set(body['scopes'])&{'book','volume'}:
            raise ValueError('不完整或未确认完整性的文本，不能支撑全书/整卷方法结论')
        origin['source_extent']=structure['body']['source_extent']
    except (OSError,ValueError,KeyError) as exc:
        issues=[{'field':'origin','message':str(exc)}]
    return origin,issues


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
