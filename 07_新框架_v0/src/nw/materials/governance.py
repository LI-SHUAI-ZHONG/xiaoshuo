"""Resolve document-level runtime layers and execute declared structural checks."""
import ast
from collections.abc import Iterator
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sqlite3

from nw.materials.layers import LayerCompiler
from nw.materials.type_adjudication import _original, _JSONObject

POLICY='source-governance-routing-v1'


def _records(value: object,locator: str='') -> Iterator[tuple[str,object]]:
    if isinstance(value,list):
        for index,member in enumerate(value):
            yield f'{locator}/{index}',member
    elif isinstance(value,dict) and any(key in value for key in ('原始条目','connections','items')):
        for key in ('原始条目','connections','items'):
            if key in value:
                yield from _records(value[key],locator+'/'+key)
    else:
        yield locator,value


def _kind(value: object, name: str) -> bool:
    return {'string':isinstance(value,str),'object':isinstance(value,dict),'array':isinstance(value,list),
            'boolean':type(value) is bool,'number':type(value) in (int,float),
            'integer':type(value) is int,'null':value is None}.get(name,True)


class GovernanceRouter:
    def __init__(self,db: sqlite3.Connection,compiler: LayerCompiler) -> None:
        self.db,self.compiler=db,compiler
        self.documents={}
        self.record_cache={}

    def document(self,source_id: str,key: str) -> dict | None:
        identity=source_id,key
        if identity in self.documents:
            return self.documents[identity]
        rows=self.db.execute('''SELECT f.id,f.key,f.source_id,f.sha256,s.file_sha256,s.path
            FROM fragments f JOIN sources s ON s.id=f.source_id
            WHERE f.source_id=? AND f.kind='source_block' AND f.key=?''',(source_id,key)).fetchall()
        if len(rows)!=1:
            self.documents[identity]=None;return None
        fragment=dict(rows[0])
        unit=self.db.execute("SELECT * FROM material_units WHERE fragment_id=? AND kind='json_document' AND locator=''",
                             (fragment['id'],)).fetchone()
        if unit is None:
            self.documents[identity]=None;return None
        unit=dict(unit)
        problems=[]
        try:
            value=_original(json.loads(self.compiler._payload(unit),object_pairs_hook=_JSONObject),problems)
        except (ValueError,UnicodeError):
            self.documents[identity]=None;return None
        if problems:
            self.documents[identity]=None;return None
        result={'source_ref':fragment,'document_ref':{k:unit[k] for k in ('id','sha256','locator','byte_start','byte_end')},
                'value':value}
        self.documents[identity]=result
        return result

    def records(self,source_id: str) -> list[tuple[str,object]]:
        if source_id not in self.record_cache:
            document=self.document(source_id,'类型静态连接总表.json')
            self.record_cache[source_id]=list(_records(document['value'])) if document else []
        return self.record_cache[source_id]

    def route(self,unit: dict) -> dict | None:
        if unit['family']!='type_links':
            return None
        value,error=self.compiler._parse(unit)
        bindings=value.get('runtime_calling_layer') if isinstance(value,dict) else None
        if error or not isinstance(bindings,list) or not bindings or any(not isinstance(b,dict) for b in bindings):
            return None
        names=[]
        for binding in bindings:
            match=re.fullmatch(r'(.+):SOURCE: ([^\r\n]+)',str(binding.get('source_ref','')))
            if not match:
                return None
            declared=match[1].replace('\\','/').casefold()
            current=unit['path'].replace('\\','/').casefold()
            if current!=declared and not current.endswith('/'+declared):
                return None
            names.append(match[2])
        if len(set(names))!=1:
            return None
        name=names[0]
        document=self.document(unit['source_id'],name)
        if document is None or not isinstance(document['value'],dict):
            return None
        original=document['value']
        locations=[]
        for binding in bindings:
            ident=binding.get('source_id')
            if not isinstance(ident,str):
                return None
            if ident in {name,name+':1'}:
                locations.append('')
            elif '字段说明' in name and isinstance(ident,str):
                try:
                    descriptor=ast.literal_eval(ident)
                except (ValueError,SyntaxError):
                    return None
                matches=[key for key,value in original.items() if isinstance(value,dict) and value==descriptor]
                if len(matches)!=1:
                    return None
                locations.append('/'+matches[0].replace('~','~0').replace('/','~1'))
            else:
                return None
        if 'items' in original and isinstance(original['items'],list):
            role='declared_collection_container'
            actual=len(original['items']);declared=original.get('count')
            validation={'check':'declared_count_matches_actual_items','status':'pass' if type(declared) is int and declared==actual else 'failed',
                        'declared_count':declared,'actual_count':actual,'creative_rules_available':actual}
            pending=[] if actual==0 else ['逐条核定实际items；容器状态不赋予条目采用权限']
        elif '字段说明' in name:
            role='field_schema';validation=self.schema_check(unit['source_id'],original)
            pending=['描述性format及语义说明继续按对应功能核验；不从格式示例猜写作事实']
        elif '枚举' in name:
            role='enumeration';validation=self.enum_check(unit['source_id'],original)
            pending=[]
        elif '验证规则' in name:
            role='validation_contract'
            rules=original.get('validation_rules',original.get('rules',[]))
            valid=isinstance(rules,list) and bool(rules) and all(isinstance(r,dict)
                and isinstance(r.get('rule_id'),str) and isinstance(r.get('rule',r.get('description')),str) for r in rules)
            validation={'check':'validation_contract_structure','status':'pass' if valid else 'failed',
                        'rules':rules,'rules_executed_as_creative_methods':0}
            pending=['逐规则接入相应的资料校验、组合设计、传播、原创性及证据消费者；结构合格不等于这些语义功能全部实现']
        elif '约束' in name or '模板' in name:
            role='project_configuration_contract'
            limits={k:v for k,v in original.items() if k.startswith('max_')}
            valid=all(type(v) is int and v>=0 for v in limits.values())
            validation={'check':'declared_configuration_structure','status':'pass' if valid else 'failed',
                        'limits':limits,'policy':original}
            pending=['逐项把声明的限制与作者决定、当前类型组合及阶段消费者对照；保留尚未实现的执行项']
        else:
            return None
        return {'policy':POLICY,'runtime_source_ref':unit,'original_source_ref':document['source_ref'],
                'document_ref':document['document_ref'],'exact_locators':sorted(set(locations)),
                'role':role,'validation':validation,'pending':pending,
                'authority':'governance_or_container_only_not_prose_permission',
                'policy_sha256':sha256(Path(__file__).read_bytes()).hexdigest()}

    def inspection_input(self,source_id: str) -> dict | None:
        document=self.document(source_id,'类型静态连接总表.json')
        if document is None:
            return None
        return {'source_ref':document['source_ref'],'document_ref':document['document_ref']}

    def enum_check(self,source_id: str,enums: dict) -> dict:
        input_ref=self.inspection_input(source_id)
        if input_ref is None:
            return {'check':'declared_enumerations','status':'not_checked','records_checked':0,
                    'missing':['确切版本的类型静态连接总表.json']}
        records=self.records(source_id);violations=[]
        forbidden=enums.get('forbidden_connection_type',[])
        for locator,record in records:
            if not isinstance(record,dict):
                violations.append({'locator':locator,'error':'record_type'});continue
            for field,allowed in enums.items():
                if field.startswith('forbidden_') or not isinstance(allowed,list) or field not in record:
                    continue
                if record[field] not in allowed:
                    violations.append({'id':record.get('connection_id'),'locator':locator,'field':field,'value':record[field]})
            if record.get('connection_type') in forbidden:
                violations.append({'id':record.get('connection_id'),'locator':locator,'field':'forbidden_connection_type','value':record['connection_type']})
        return {'check':'declared_enumerations','status':'failed' if violations else 'pass',
                'records_checked':len(records),'input_ref':input_ref,'violations':violations}

    def schema_check(self,source_id: str,schema: dict) -> dict:
        input_ref=self.inspection_input(source_id)
        if input_ref is None:
            return {'check':'declared_types_enums_and_explicit_ranges','status':'not_checked','records_checked':0,
                    'missing':['确切版本的类型静态连接总表.json']}
        records=self.records(source_id);violations=[]
        enum_document=self.document(source_id,'类型连接枚举.json')
        enums=enum_document['value'] if enum_document else {}
        missing=[]
        for field,spec in schema.items():
            if not isinstance(spec,dict) or not spec.get('enum_ref'):
                continue
            if spec['enum_ref']!='类型连接枚举.json' or not isinstance(enums,dict) or not isinstance(enums.get(field),list):
                missing.append(f'{field}: {spec["enum_ref"]} 中的确切枚举')
        if missing:
            return {'check':'declared_types_enums_and_explicit_ranges','status':'not_checked',
                    'records_checked':0,'input_ref':input_ref,'missing':missing}
        for locator,record in records:
            if not isinstance(record,dict):
                violations.append({'locator':locator,'error':'record_type'});continue
            reference={'id':record.get('connection_id'),'locator':locator}
            for field,spec in schema.items():
                if not isinstance(spec,dict):
                    continue
                if field not in record:
                    if spec.get('required') is True:
                        violations.append({**reference,'field':field,'error':'required'})
                    continue
                value=record[field];expected=spec.get('type')
                if isinstance(expected,str) and not _kind(value,expected):
                    violations.append({**reference,'field':field,'error':'type','expected':expected})
                    continue
                allowed=spec.get('enum')
                if spec.get('enum_ref')=='类型连接枚举.json':
                    allowed=enums.get(field)
                if isinstance(allowed,list) and value not in allowed:
                    violations.append({**reference,'field':field,'error':'enum','value':value})
                if isinstance(value,str) and isinstance(spec.get('pattern'),str):
                    try:
                        valid=re.fullmatch(spec['pattern'],value) is not None
                    except re.error:
                        valid=False
                    if not valid:
                        violations.append({**reference,'field':field,'error':'pattern','value':value})
                if type(value) in (int,float):
                    if not math.isfinite(value):
                        violations.append({**reference,'field':field,'error':'non_finite'})
                    for bound,comparison in (('min',lambda x,y:x<y),('max',lambda x,y:x>y),
                                             ('minimum',lambda x,y:x<y),('maximum',lambda x,y:x>y)):
                        if type(spec.get(bound)) in (int,float) and comparison(value,spec[bound]):
                            violations.append({**reference,'field':field,'error':bound,'value':value})
        return {'check':'declared_types_enums_and_explicit_ranges','status':'failed' if violations else 'pass',
                'records_checked':len(records),'input_ref':input_ref,'violations':violations}
