"""Evidence-local fragments refine a shared graph, never a bag of method labels."""
from copy import deepcopy

from nw.studio.corpus_catalog import FIELDS
from nw.studio.corpus_checks import graph_issues
from nw.studio.corpus_contract import normalize_document


def resolve_fragment(raw: dict, document: dict, content: str, *, span: dict | None,
                     prefix: str, phase: str, domain: str | None = None,
                     event_allowlist: set | None = None, evidence_allowlist: set | None = None) -> dict:
    allowed={*FIELDS,'overview','uncertainties','character_updates'}
    if not isinstance(raw,dict) or set(raw)-allowed:raise ValueError('模型应返回结构片段，不是用法条目或任意字段')
    patch=deepcopy(raw)
    if phase in ('survey','detail') and not patch.get('events') and not patch.get('uncertainties'):
        raise ValueError('原文片段既无观察也无待核实说明，不能作为已完成分析')
    if event_allowlist is not None:
        for link in patch.get('links',[]):
            if link.get('source') not in event_allowlist or link.get('target') not in event_allowlist:
                raise ValueError('不能引用本次核对上下文未提供的关系端点')
        prior={t['id']:set(t['node_ids']) for t in document['threads']}
        for thread in patch.get('threads',[]):
            if not set(thread.get('node_ids',[]))<=event_allowlist|prior.get(thread.get('id'),set()):
                raise ValueError('线索使用了未提供的事件观察')
    if evidence_allowlist is not None:
        for section in ('threads','links','domains','character_updates'):
            prior={r.get('id',r.get('domain')):set(r['evidence_ids']) for r in document['characters' if section=='character_updates' else section]}
            for record in patch.get(section,[]):
                old=prior.get(record.get('id',record.get('domain')),set())
                if not set(record.get('evidence_ids',[]))<=evidence_allowlist|old:raise ValueError('分析引用了本次未提供的新证据')
    if phase in ('overview','relations'):
        if any(patch.get(k) for k in ('units','events','characters','evidence')):
            raise ValueError('整合只能引用已有观察，不能重造原文、人物或事件')
    if phase=='survey' and any(patch.get(k) for k in ('units','threads','links','domains','overview','character_updates')):
        raise ValueError('通读阶段只收集有证据的人物与总览事件，不能直接提炼方法')
    if phase=='detail' and patch.get('overview'):raise ValueError('章场细拆不能覆盖冻结的全书总览')
    for section in ('units','characters','events','evidence'):
        old={r['id']:r for r in document[section]}
        for row in patch.get(section,[]):
            if row.get('id') not in old and not str(row.get('id','')).startswith(prefix+'_'):
                raise ValueError('新观察标识须使用本次调用的命名空间')
            if section=='evidence':
                quote=row.get('quote','')
                if not isinstance(quote,str) or not span:raise ValueError('新证据必须来自当前原文片段')
                start=row.get('start')
                if start is None:
                    local=content[span['start']:span['end']].find(quote)
                    if local<0:raise ValueError('模型引文不在本次原文中')
                    if content.find(quote,span['start']+local+1,span['end'])>=0:raise ValueError('重复引文必须指定绝对字符起点')
                    start=span['start']+local
                end=start+len(quote)
                if not span['start']<=start<end<=span['end']:raise ValueError('模型引文超出当前片段')
                if 'end' in row and row['end']!=end:raise ValueError('证据终点不符')
                row.update(start=start,end=end)
            if section=='units' and (row.get('level')!='scene' or not span or row.get('parent_id')!=span['unit_id']):
                raise ValueError('细拆只能在本章新增实际场景范围')
            if section=='units':row['boundary_basis']='analyst_inference'
            if section=='events':
                if row.get('granularity')!=('overview' if phase=='survey' else 'detail'):raise ValueError('事件粒度与当前阶段不符')
                if not span:raise ValueError('事件必须来自原文阅读阶段')
    if domain:
        if any(t.get('domain')!=domain for t in patch.get('threads',[])) or any(d.get('domain')!=domain for d in patch.get('domains',[])):
            raise ValueError('跨章核对不得修改其他制作职责')
    result=merge_fragment(document,patch)
    normalized=normalize_document(result,content)
    if span:
        units={u['id']:u for u in normalized['units']}
        current_evidence={e['id'] for e in normalized['evidence'] if span['start']<=e['start']<e['end']<=span['end']}
        coarse={e['id'] for e in document['events'] if e['granularity']=='overview' and e['unit_id']==span['unit_id']}
        for event in patch.get('events',[]):
            unit=units.get(event['unit_id'],{})
            if event['unit_id']!=span['unit_id'] and not (phase=='detail' and unit.get('level')=='scene' and unit.get('parent_id')==span['unit_id']):
                raise ValueError('新增事件必须属于当前读取的章节/场景')
            if not set(event['evidence_ids'])&current_evidence:raise ValueError('新增事件必须引用当前原文片段的证据')
            if phase=='detail' and not set(event['parent_event_ids'])<=coarse:
                raise ValueError('细节事件必须对应本章实际提供的总览节点')
    checks=graph_issues(normalized,len(content))
    errors=[r['message'] for r in checks if r['severity']=='error' and r['field'] not in ('overview','domains','source_extent','coverage')
            and r['message']!='尚无有证据的事件节点']
    if errors:raise ValueError('；'.join(errors[:8]))
    return patch


def merge_fragment(document: dict, patch: dict) -> dict:
    result=deepcopy(document)
    for section in FIELDS:
        key='domain' if section=='domains' else 'id'
        indexed={r[key]:r for r in result[section]}
        for incoming in patch.get(section,[]):
            prior=indexed.get(incoming[key])
            if prior and prior!=incoming:
                if section=='threads':
                    if prior['domain']!=incoming['domain']:raise ValueError('不能偷换同一线索的职责')
                    incoming=deepcopy(incoming)
                    for field in ('node_ids','characters','evidence_ids'):
                        incoming[field]=list(dict.fromkeys([*prior[field],*incoming[field]]))
                elif section=='domains':pass
                elif section=='units' and prior['level']=='scene' and incoming['parent_id']==prior['parent_id'] and incoming['start']==prior['start'] and incoming['end']>=prior['end']:pass
                else:raise ValueError('观察标识冲突，不能覆盖已有来源记录：'+str(incoming[key]))
            indexed[incoming[key]]=deepcopy(incoming)
        result[section]=list(indexed.values())
    people={r['id']:r for r in result['characters']}
    for row in patch.get('character_updates',[]):
        prior=people.get(row.get('id'))
        if not prior or row.get('name')!=prior['name'] or not set(prior['evidence_ids'])<=set(row.get('evidence_ids',[])):
            raise ValueError('人物归并/更新必须保留原身份和证据')
        people[row['id']]=deepcopy(row)
    result['characters']=list(people.values())
    events={e['id']:e for e in result['events']};evidence={e['id']:e for e in result['evidence']}
    def position(ident: str) -> tuple:
        event=events.get(ident,{})
        return (min((evidence[k]['start'] for k in event.get('evidence_ids',[]) if k in evidence),default=10**12),
                event.get('granularity')!='overview',ident)
    for thread in result['threads']:
        thread['node_ids']=sorted(thread['node_ids'],key=position)
    if patch.get('overview'):result['overview'].update(deepcopy(patch['overview']))
    result['uncertainties']=list(dict.fromkeys([*result['uncertainties'],*patch.get('uncertainties',[])]))
    return result
