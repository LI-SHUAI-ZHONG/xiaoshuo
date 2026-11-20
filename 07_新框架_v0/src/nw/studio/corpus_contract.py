"""Normalize analytical records and validate exact source evidence."""
from copy import deepcopy
import re

from nw.studio.corpus_catalog import DETAILS, DOMAINS, FIELDS, LEVELS, LINKS, OVERVIEW, domains_for
from nw.studio.library_util import encode

ID = re.compile(r'^[A-Za-z][A-Za-z0-9_]{0,95}$')
REF_LISTS = {'evidence_ids','characters','parent_event_ids','node_ids'}
LIMITS = {'units':10000,'characters':3000,'events':30000,'threads':15000,'links':60000,'evidence':60000,'domains':len(DOMAINS)}


def string(value: object, label: str, limit: int = 4000, *, strip: bool = True) -> str:
    if not isinstance(value,str) or len(value)>limit:
        raise ValueError(f'{label}须为不超过{limit}字符的文本')
    return value.strip() if strip else value


def identifier(value: object, *, nullable: bool = False) -> str | None:
    if nullable and value in (None,''): return None
    if not isinstance(value,str) or not ID.fullmatch(value): raise ValueError('记录标识必须以字母开头，只含字母、数字及下划线')
    return value


def references(value: object) -> list[str]:
    if not isinstance(value,list) or len(value)>30000: raise ValueError('引用须为有限列表')
    result=[identifier(v) for v in value]
    if len(set(result))!=len(result): raise ValueError('同一记录中的引用不能重复')
    return result


def normalize_document(raw: dict, content: str) -> dict:
    if not isinstance(raw,dict) or set(raw)-{'schema_version','source_extent','overview',*FIELDS,'uncertainties'}:
        raise ValueError('拆解结构含未知字段或不是对象')
    version=raw.get('schema_version',1)
    domains=domains_for(version)
    extent=raw.get('source_extent',{'status':'unknown','note':''})
    if not isinstance(extent,dict) or set(extent)!={'status','note'} or extent['status'] not in ('complete','excerpt','unknown'):
        raise ValueError('请明确参考文本完整性及作者说明')
    overview=raw.get('overview',{})
    if not isinstance(overview,dict) or set(overview)-OVERVIEW.keys(): raise ValueError('全书总览字段无效')
    result={'schema_version':version,'source_extent':{'status':extent['status'],'note':string(extent['note'],'完整性说明')},
            'overview':{k:string(overview.get(k,''),OVERVIEW[k],12000) for k in OVERVIEW}}
    for section,fields in FIELDS.items():
        rows=raw.get(section,[])
        if not isinstance(rows,list) or len(rows)>LIMITS[section]: raise ValueError('拆解记录数量超出范围：'+section)
        result[section]=[]
        for row in rows:
            if not isinstance(row,dict) or set(row)!=set(fields): raise ValueError('记录字段不完整或包含未知字段：'+section)
            clean={}
            for key,value in row.items():
                if key in REF_LISTS: clean[key]=references(value)
                elif key in ('id','unit_id','source','target'): clean[key]=identifier(value)
                elif key in ('parent_id','thread_id','canonical_id'): clean[key]=identifier(value,nullable=True)
                elif key in ('start','end'):
                    if type(value) is not int or value<0: raise ValueError('原作字符位置必须为非负整数')
                    clean[key]=value
                elif key=='story_order':
                    if value is not None and (type(value) is not int or value<0): raise ValueError('故事顺序必须为非负整数或未知')
                    clean[key]=value
                elif key=='details':
                    if row.get('domain') not in DETAILS or not isinstance(value,dict) or set(value)!=set(DETAILS[row['domain']]):
                        raise ValueError('请按具体制作职责填写分析字段')
                    clean[key]={k:string(v,DETAILS[row['domain']][k]) for k,v in value.items()}
                else: clean[key]=string(value,fields[key],1500 if key=='quote' else 4000,strip=key!='quote')
            if section=='units':
                if clean['level'] not in LEVELS or clean['boundary_basis'] not in ('source_file','source_heading','analyst_inference','author_confirmed'):
                    raise ValueError('层级或边界依据无效')
                if not 0<=clean['start']<clean['end']<=len(content): raise ValueError('卷章场范围越界')
            if section=='events' and clean['granularity'] not in ('overview','detail'): raise ValueError('事件粒度无效')
            if section in ('threads','domains'):
                if clean['domain'] not in domains: raise ValueError('制作职责不属于本版拆解结构')
                allowed=('open','resolved','uncertain') if section=='threads' else ('observed','not_observed','uncertain')
                if clean['status'] not in allowed: raise ValueError('分析状态无效')
            if section=='links' and (clean['kind'] not in LINKS or clean['certainty'] not in ('observed','inferred')):
                raise ValueError('关系或观察/推断身份无效')
            if section=='evidence':
                if not clean['quote'].strip() or clean['end']!=clean['start']+len(clean['quote']) or content[clean['start']:clean['end']]!=clean['quote']:
                    raise ValueError('拆解证据与原作字符位置不一致')
            result[section].append(clean)
    unknown=raw.get('uncertainties',[])
    if not isinstance(unknown,list) or len(unknown)>10000: raise ValueError('待核实项必须为列表')
    result['uncertainties']=[string(value,'待核实项') for value in unknown]
    if len(encode(result).encode('utf-8'))>32*1024*1024: raise ValueError('结构超过32MiB，未截断保存；请调整分析粒度或分范围维护')
    return result


def canonical(raw: dict, content: str) -> dict:
    return normalize_document(deepcopy(raw),content)
