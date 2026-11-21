"""Immutable source structures with independent author review."""
from copy import deepcopy
import hashlib
import json

from nw.studio.corpus_catalog import FIELDS, SCHEMA_VERSION, corpus_catalog, require_current_schema
from nw.studio.corpus_checks import graph_issues
from nw.studio.corpus_contract import normalize_document
from nw.studio.corpus_index import empty_document, range_coverage
from nw.studio.library_util import encode, timestamp


def body_hash(body: dict) -> str:
    return hashlib.sha256(encode(body).encode('utf-8')).hexdigest()


class CorpusMixin:
    def corpus_catalog(self, version: int = SCHEMA_VERSION) -> dict:
        return corpus_catalog(version)

    def _corpus_row(self, book_id: str, version: int, conn: object) -> dict:
        head=conn.execute('SELECT * FROM corpus_structures WHERE book_id=?',(book_id,)).fetchone()
        raw=conn.execute('SELECT * FROM corpus_structure_versions WHERE book_id=? AND version=?',(book_id,version)).fetchone()
        if not head or not raw:raise FileNotFoundError('拆解结构版本不存在')
        body=json.loads(raw['body_json']);coverage=json.loads(raw['coverage_json'])
        if body_hash(body)!=raw['body_sha256']:raise ValueError('拆解结构版本完整性校验失败')
        source_issues=[]
        book=self._staging_row(book_id)
        try:
            content=self._book_text(book)
            if raw['source_sha256']!=book['sha256']:raise ValueError('拆解的来源版本已改变')
            if book['status']=='rejected':raise ValueError('参考作品已撤回')
        except (OSError,ValueError) as exc:
            source_issues=[{'field':'source','message':str(exc),'severity':'error'}]
            content=''
        issues=graph_issues(body,len(content) if content else max((u['end'] for u in body['units']),default=0),coverage,content=content or None)
        review=conn.execute('SELECT * FROM corpus_structure_reviews WHERE book_id=? AND version=?',(book_id,version)).fetchone()
        state={'approve':'approved','reject':'rejected'}.get(review['decision'],'draft') if review else 'draft'
        return {'book_id':book_id,'version':version,'latest_version':head['latest_version'],'approved_version':head['approved_version'],
            'body':body,'body_sha256':raw['body_sha256'],'source_sha256':raw['source_sha256'],'coverage':coverage,
            'status':'source_unavailable' if source_issues else state,'review':dict(review) if review else None,
            'issues':issues+source_issues,'available':state=='approved' and not source_issues and not any(i['severity']=='error' for i in issues),
            'initialized':True,'created_at':raw['created_at'],'job_id':raw['job_id']}

    def get_corpus(self, book_id: str, version: int | None = None) -> dict:
        book=self._staging_row(book_id)
        if version is not None and (type(version) is not int or version<1):raise ValueError('拆解版本须为正整数')
        with self.connect() as conn:
            head=conn.execute('SELECT * FROM corpus_structures WHERE book_id=?',(book_id,)).fetchone()
            if not head:
                if version is not None:raise FileNotFoundError('拆解结构版本不存在')
                result={'book_id':book_id,'initialized':False,'latest_version':0,'approved_version':None,'version':0,
                        'body':empty_document(self._book_text(book)),'coverage':{},'issues':[],'available':False,'history':[]}
            else:
                result=self._corpus_row(book_id,version or head['latest_version'],conn)
                result['history']=[dict(r) for r in conn.execute('SELECT v.version,v.body_sha256,v.created_at,r.decision '
                    'FROM corpus_structure_versions v LEFT JOIN corpus_structure_reviews r ON r.book_id=v.book_id AND r.version=v.version '
                    'WHERE v.book_id=? ORDER BY v.version DESC',(book_id,))]
            result['derived_methods']=[dict(r) for r in conn.execute('SELECT o.method_id,o.method_version,o.structure_version '
                'FROM corpus_method_origins o WHERE o.book_id=? ORDER BY o.created_at DESC',(book_id,))]
        result['jobs']=self.list_corpus_jobs(book_id)['jobs']
        from nw.studio.corpus_stats import corpus_statistics
        result['statistics']=corpus_statistics(result['body'],result['coverage'])
        return result

    def _store_corpus(self, conn: object, book_id: str, body: dict, expected: int, coverage: dict,
                      *, job_id: str | None = None) -> int:
        head=conn.execute('SELECT * FROM corpus_structures WHERE book_id=?',(book_id,)).fetchone()
        latest=head['latest_version'] if head else 0
        if latest!=expected:raise ValueError('拆解结构已更新，请刷新；旧版本未覆盖')
        now=timestamp();version=latest+1
        book=conn.execute('SELECT * FROM staging_books WHERE id=?',(book_id,)).fetchone()
        if not book or book['status']=='rejected':raise ValueError('来源作品已撤回，不能保存新分析')
        content=self._book_text(dict(book));body=normalize_document(body,content)
        if head:conn.execute('UPDATE corpus_structures SET latest_version=?,updated_at=? WHERE book_id=?',(version,now,book_id))
        else:conn.execute('INSERT INTO corpus_structures VALUES(?,?,NULL,?,?)',(book_id,version,now,now))
        conn.execute('INSERT INTO corpus_structure_versions VALUES(?,?,?,?,?,?,?,?)',
            (book_id,version,book['sha256'],encode(body),body_hash(body),encode(coverage),job_id,now))
        if not head or head['approved_version'] is None:
            conn.execute("UPDATE staging_books SET status='pending_verify',progress=1,error='',updated_at=? "
                         "WHERE id=? AND status NOT IN ('pending_review','rejected')",(now,book_id))
        return version

    def save_corpus(self, book_id: str, request: dict) -> dict:
        if not isinstance(request,dict) or set(request)-{'expected_version','body','reviewed_units'}:raise ValueError('拆解保存请求无效')
        expected=request.get('expected_version')
        if type(expected) is not int or expected<0:raise ValueError('请提供当前拆解版本，新结构为0')
        raw=request.get('body')
        if not isinstance(raw,dict) or raw.get('schema_version')!=SCHEMA_VERSION:
            raise ValueError('新建或修订须使用当前拆解结构版本，请刷新目录再保存')
        book=self._staging_row(book_id);body=normalize_document(raw,self._book_text(book))
        reviewed=request.get('reviewed_units',[])
        chapters={u['id'] for u in body['units'] if u['level']=='chapter'}
        if not isinstance(reviewed,list) or any(v not in chapters for v in reviewed) or len(reviewed)!=len(set(reviewed)):
            raise ValueError('作者确认阅读的范围必须来自当前章节目录')
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            active=conn.execute("SELECT id FROM corpus_jobs WHERE book_id=? AND status IN ('pending','running')",(book_id,)).fetchone()
            if active:raise ValueError('拆解任务正在运行，请先暂停再编辑结构')
            prior=conn.execute("SELECT coverage_json, json_extract(body_json,'$.schema_version') FROM corpus_structure_versions "
                               "WHERE book_id=? AND version=?",(book_id,expected)).fetchone()
            # The old version keeps its full reading record. Its detail pass did not examine the new domains.
            coverage=json.loads(prior[0]) if prior and prior[1] == SCHEMA_VERSION else {}
            coverage.update(reviewed_units=reviewed,manual_revision=True)
            self._store_corpus(conn,book_id,body,expected,coverage)
        return self.get_corpus(book_id)

    def initialize_corpus(self, book_id: str, request: dict) -> dict:
        if set(request)-{'extent','note','expected_version'}:raise ValueError('目录初始化请求无效')
        book=self._staging_row(book_id)
        body=empty_document(self._book_text(book),request.get('extent','unknown'),request.get('note',''))
        return self.save_corpus(book_id,{'expected_version':request.get('expected_version',0),'body':body})

    def edit_corpus_record(self, book_id: str, request: dict) -> dict:
        if set(request)-{'expected_version','section','row','remove_id','reviewed_units'}:raise ValueError('结构编辑请求无效')
        current=self.get_corpus(book_id);section=request.get('section')
        if request.get('expected_version')!=current['latest_version']:raise ValueError('拆解已更新，请刷新后再修改')
        body=deepcopy(current['body'])
        body['schema_version']=SCHEMA_VERSION
        if section=='read_confirmation':
            return self.save_corpus(book_id,{'body':body,'expected_version':current['latest_version'],'reviewed_units':request.get('row')})
        if section in ('overview','source_extent','uncertainties'):body[section]=request.get('row')
        elif section in FIELDS:
            key='domain' if section=='domains' else 'id'
            row=request.get('row');remove=request.get('remove_id')
            if remove is not None:
                if row is not None:raise ValueError('不能同时移除并修改记录')
                body[section]=[r for r in body[section] if r[key]!=remove]
            elif isinstance(row,dict) and key in row:
                found=next((i for i,r in enumerate(body[section]) if r[key]==row[key]),None)
                if found is None:body[section].append(row)
                else:body[section][found]=row
            else:raise ValueError('记录必须有明确标识')
        else:raise ValueError('未知结构板块')
        reviewed=current.get('coverage',{}).get('reviewed_units',[]) if current['body'].get('schema_version')==SCHEMA_VERSION else []
        return self.save_corpus(book_id,{'body':body,'expected_version':current['latest_version'],
            'reviewed_units':request.get('reviewed_units',reviewed)})

    def review_corpus(self, book_id: str, request: dict) -> dict:
        version=request.get('version');decision=request.get('decision');note=request.get('note','')
        if type(version) is not int or decision not in ('approve','reject') or not isinstance(note,str) or not note.strip() or len(note)>4000:
            raise ValueError('请指定版本、批准/退回及审核依据')
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE');row=self._corpus_row(book_id,version,conn)
            if version!=row['latest_version']:raise ValueError('只能审核当前最新结构版本')
            if row['review']:raise ValueError('该版本已审核；修订必须新增版本')
            if decision=='approve':
                require_current_schema(row['body'].get('schema_version', 1))
                errors=[r['message'] for r in row['issues'] if r['severity']=='error']
                if errors:raise ValueError('结构尚不能批准：'+'；'.join(errors[:12]))
                limited=row['body']['source_extent']['status']!='complete' or row['body']['uncertainties'] or row['issues']
                if limited and request.get('accept_limitations') is not True:raise ValueError('请明确确认当前覆盖限制与待核实项，不能作为完整作品结论')
                if self._staging_row(book_id)['status']=='pending_review':raise ValueError('请先确认作品类型')
            conn.execute('INSERT INTO corpus_structure_reviews VALUES(?,?,?,?,?)',(book_id,version,decision,note.strip(),timestamp()))
            if decision=='approve':
                conn.execute('UPDATE corpus_structures SET approved_version=?,updated_at=? WHERE book_id=?',(version,timestamp(),book_id))
                conn.execute("UPDATE staging_books SET status='archived',updated_at=? WHERE id=? AND status!='rejected'",(timestamp(),book_id))
        return self.get_corpus(book_id)
