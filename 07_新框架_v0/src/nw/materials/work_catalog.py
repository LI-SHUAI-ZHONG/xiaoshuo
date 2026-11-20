"""A readable method desk, separate from approval to assert source/story facts."""
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3

from nw.materials.adjudication import adjudication_status
from nw.materials.catalog import show_fragment,_connect
from nw.materials.type_adjudication import _original
from nw.selection import _keywords
from nw.task_models import canonical, content_sha256


def method_role(original: object) -> str:
    if isinstance(original,str):
        meaningful=re.sub(r'(?m)^#+[^\n]+','',original).strip()
        meaningful=re.sub(r'【[^】\n]+】','',meaningful)
        meaningful=re.sub(r'(?im)^\s*(?:无|待补|未提供|暂无|N/A|[-| :]+)\s*$','',meaningful).strip()
        operational=any(word in meaningful for word in ('检查','核对','比较','必须','禁止','应当','需要'))
        return 'project_method' if len(meaningful)>=12 or len(meaningful)>=8 and operational else 'navigation_only'
    if isinstance(original,dict):
        if 'items' in original and not original['items']:
            return 'navigation_only'
        functional=('preconditions','selection_constraints','parameters','preferred_expressions',
                    'candidate_actions','candidate_effects','conditions','condition','effects','effect')
        if any(original.get(key) not in (None,'',[],{}) for key in functional):
            return 'project_method'
        names={str(original.get(key,'')).strip() for key in ('canonical_name','name','title','type_name','label')}
        for key in ('definition','description','rule','scope'):
            value=original.get(key)
            if isinstance(value,str) and value.strip() and value.strip() not in names|{'无','待补','未提供','暂无','名称','规范名称'}:
                return 'project_method'
    return 'navigation_only'


def original_text(raw: str) -> tuple[str,object]:
    if raw.lstrip().startswith(('{','[')):
        try:
            value=_original(json.loads(raw),[])
            return canonical(value),value
        except ValueError:
            return raw,{}
    text=re.split(r'【运行层升级】|<details[^>]*>\s*<summary>运行层升级',raw,maxsplit=1)[0].strip()
    return text,text


_META_BIGRAMS = frozenset({'小说', '一部', '写一', '本书', '全书', '故事', '作品', '创作', '只输', '输出', '正文'})


class SourceDesk:
    def __init__(self,workspace: Path,*,test_mode: bool=False) -> None:
        self.workspace=workspace
        self.test_mode=test_mode
        status=adjudication_status(workspace)['status']
        if status=='stale':
            raise ValueError('STALE_MATERIAL: rebuild the method source ledger')
        self.path=workspace/'materials/adjudication.db'
        self.has_reviews=status=='current'
        if self.has_reviews:
            with closing(self._connect()) as db:
                self.rows=[dict(row) for row in db.execute('''SELECT p.id,p.key,p.profile,p.state,p.sha256,p.file_sha256,
                    p.path,json_extract(c.payload_json,'$.meaning') AS meaning,
                    json_extract(c.payload_json,'$.source_refs[0].fragment_key') AS fragment_key,
                    coalesce(json_extract(c.payload_json,'$.contract.guidance'),
                             json_extract(c.payload_json,'$.contract.method_fields'),
                             json_extract(c.payload_json,'$.contract.definition'),'') AS function_text FROM positions p
                    JOIN contracts c ON c.owner_id=p.owner_id WHERE p.id=p.owner_id ORDER BY p.path,p.key,p.id''')]
                known={row['id'] for row in self.rows}
                for row in db.execute('SELECT owner_id,payload_json FROM contracts ORDER BY owner_id'):
                    if row['owner_id'] in known:continue
                    review=json.loads(row['payload_json'])
                    ref=next((r for r in review['source_refs'] if r['id']==row['owner_id']),None)
                    if ref is None:raise ValueError('MATERIAL_WORK: source contract has no retrievable original reference')
                    position=db.execute('SELECT * FROM positions WHERE id=?',(row['owner_id'],)).fetchone()
                    base=dict(position) if position is not None else {}
                    self.rows.append({'id':row['owner_id'],'key':ref.get('fragment_key',base.get('key',row['owner_id'])),
                        'profile':review['profile'],'state':review['state'],'sha256':ref['sha256'],
                        'file_sha256':ref['file_sha256'],'path':ref.get('path',base.get('path','')),
                        'fragment_key':ref.get('fragment_key'),
                        'meaning':review['meaning'],'function_text':canonical(review.get('contract',{}))})
        else:
            # Reading an indexed method is independent of permission to assert
            # its rule as confirmed. Legacy explicitly pinned sources can be
            # studied without silently manufacturing a qualification ledger.
            from nw.materials.route_catalog import _FRAGMENTS,_UNITS
            from nw.materials.routing import disposition
            self.rows=[]
            with closing(_connect(workspace,write=False)) as db:
                for query in (_FRAGMENTS+" WHERE f.kind NOT IN ('library_upgrade','quarantined')",
                              _UNITS+" WHERE u.kind IN ('record','embedded_entry','embedded_block') AND u.origin='source'"):
                    for raw in db.execute(query):
                        row=dict(raw);row.update(profile=disposition(row)[0],state='not_adjudicated',meaning='')
                        self.rows.append(row)
        from nw.materials.work_knowledge import work_knowledge_only
        self.work_knowledge_only_ids = frozenset(row['id'] for row in self.rows
                                                  if work_knowledge_only(row.get('fragment_key') or row.get('key')))
        self.rows = [row for row in self.rows if row['id'] not in self.work_knowledge_only_ids]
        self.by_id={row['id']:row for row in self.rows}
        from nw.materials.semantic_catalog import load_semantic_metadata
        semantics=load_semantic_metadata(workspace)
        for row in self.rows:
            if row['id'] in semantics:row.update(semantics[row['id']])
        self.semantic_cache={}
        from nw.materials.binding_reviews import load_reviews
        self.binding_reviews=load_reviews(workspace,test_mode=test_mode)
        for row in self.rows:
            review=self.binding_reviews.get(row['id'],{})
            if all(review.get('source',{}).get(k)==row.get(k) for k in ('id','sha256','file_sha256')):
                row['execution_stages']=list(dict.fromkeys(u['stage'] for u in review['uses']))
                row['routing_authority']='source_workflow_review_requires_exact_original_check'

    def _connect(self) -> sqlite3.Connection:
        db=sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
        return db

    def directory(self) -> dict:
        topics={};examples={}
        for row in self.rows:
            if len(examples.setdefault(row['profile'],[]))<2:
                examples[row['profile']].append({key:row[key] for key in ('id','key','meaning')})
            match=re.match(r'(\d+)\.',row['key'] or '')
            if match and row['profile'] not in {'type_identity','type_combination','type_link','metadata'}:
                topics.setdefault(match[1],row['key'])
        return {'purpose':'按任务功能检索和研读，不能用标题代替原文；可继续翻页和沿引用读取',
                'source_states':dict(Counter(row['state'] for row in self.rows)),
                'functions':dict(Counter(row['profile'] for row in self.rows)),
                'method_examples':examples,
                'topics':topics,'operations':['search(query,cursor)','read(id)'],
                'state_policy':'来源资格与项目方法用途分开；template、blocked仍可研读，不自动升为事实'}

    def search(self,query: str,*,cursor: int=0,limit: int=12,profiles: set[str] | None=None,
               step_uses: dict[str, str] | None = None) -> dict:
        if not isinstance(query,str) or not query.strip() or type(cursor) is not int or cursor<0 or type(limit) is not int or not 1<=limit<=40:
            raise ValueError('MATERIAL_WORK: invalid source search')
        raw_words=_keywords([query])
        words=(raw_words-_META_BIGRAMS) if len(raw_words)>4 and (raw_words-_META_BIGRAMS) else raw_words
        qfold=query.strip().casefold()
        ranked=[]
        rows = self.rows if step_uses is None else (self.by_id[ident] for ident in step_uses)
        for row in rows:
            if profiles is not None and row['profile'] not in profiles:continue
            key=row['key'] or '';meaning=row['meaning'] or ''
            functional=str(row.get('function_text','')).casefold()
            if step_uses is not None:
                meaning = step_uses[row['id']]
                functional = ''
            score=(50 if qfold in key.casefold() else (20 if len(qfold)<=40 and qfold in meaning.casefold() else 0))
            score+=len(words&_keywords([key]))*8+len(words&_keywords([meaning]))*3
            score+=sum(word.casefold() in functional for word in words)
            if score:
                result={key:row[key] for key in ('id','key','profile','state','meaning','file_sha256','sha256')}
                if row.get('execution_stages'):result['execution_stages']=row['execution_stages']
                if step_uses is not None:
                    result['meaning'] = meaning[:240]
                elif row.get('function_text'):
                    result['function_text']=row['function_text']
                ranked.append((-score,row['id'],result))
        ranked.sort(key=lambda item:item[:2]);page=ranked[cursor:cursor+limit]
        return {'query':query,'total':len(ranked),'cursor':cursor,
                'next_cursor':cursor+limit if cursor+limit<len(ranked) else None,
                'items':[row[2] for row in page]}

    def read(self,ident: str) -> dict:
        if not isinstance(ident,str) or ident not in self.by_id:
            raise ValueError('MATERIAL_WORK: source is outside the indexed method desk')
        row=self.by_id[ident]
        raw=show_fragment(self.workspace,ident)
        if raw['sha256']!=row['sha256']:
            raise ValueError('STALE_MATERIAL: method source hash changed')
        review={'missing':['尚未核定为已确认来源规则；只研读原文并产生项目候选方法']}
        if self.has_reviews:
            with closing(self._connect()) as db:
                review=json.loads(db.execute('SELECT payload_json FROM contracts WHERE owner_id=?',(ident,)).fetchone()[0])
        text,original=original_text(raw['text'])
        layers=review.get('layer_contract') or {}
        applications=[]
        for pair in layers.get('pairs',[]):
            runtime=show_fragment(self.workspace,pair['id'])
            if runtime['sha256']!=pair['source_ref']['sha256']:
                raise ValueError('STALE_MATERIAL: application layer hash changed')
            applications.append({'source_ref':pair['source_ref'],'text':runtime['text'],
                                 'aligned_fields':pair['aligned_fields'],'rejected_fields':pair['rejected_fields']})
        return {'source':{key:row[key] for key in ('id','key','profile','path','file_sha256','sha256')},
                'source_state':row['state'],'original_text':text,'original_text_sha256':content_sha256(text),
                'application_layers':applications,'source_issues':{key:review.get(key,[]) for key in ('missing','conflicts')},
                'related_sources':review.get('related',[]),'use_mode':method_role(original),
                'authority':'project_candidate_only_not_source_repair_or_story_fact',
                'boundary':'按原义实例化本项目方法；不继承旧授权，不据错误评分证明有效，不把模板自动生成completed事件。'}

    def verify(self,sources: list[dict]) -> None:
        for source in sources:
            fresh=self.read(source['source']['id'])
            if content_sha256(fresh)!=content_sha256(source):
                raise ValueError('STALE_MATERIAL: studied original or application layer changed')

    def semantic_contract(self,source: dict) -> dict:
        from nw.materials.source_context import source_context
        from nw.materials.source_semantics import compile_semantics
        key=source['source']['id'],content_sha256(source)
        if key not in self.semantic_cache:
            self.semantic_cache[key]=compile_semantics(source,source_context(self.workspace,source))
        return self.semantic_cache[key]

    def binding_review(self,source: dict,stage: str | None=None,scope: str | None=None) -> dict | None:
        from nw.materials.binding_reviews import reviewed_source
        return reviewed_source(source,self.binding_reviews,test_mode=self.test_mode,stage=stage,scope=scope)
