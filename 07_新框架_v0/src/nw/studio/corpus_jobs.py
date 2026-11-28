"""Job lifecycle for hierarchical corpus analysis, sharing book execution locks."""
from dataclasses import replace
import json
import threading
from types import SimpleNamespace
from uuid import uuid4

from nw.call_control import execution_lock
from nw.config import ConfigRequired, load_config, make_provider, resolve_stage_runtime
from nw.studio.corpus_calls import artifact
from nw.studio.corpus_catalog import SCHEMA_VERSION, domains_for, require_current_schema
from nw.studio.corpus_checks import graph_issues
from nw.studio.corpus_direct import (
    DEFAULT_TRACK_IDS,
    TARGETED_TRACKS,
    estimate_targeted_calls,
    select_targeted_spans,
)
from nw.studio.corpus_index import empty_document, source_spans
from nw.studio.library_util import encode, timestamp

ACTIVE=('pending','running','paused','failed')
DECOMPOSE_MIN_TIMEOUT = 300.0


def runtime_profile(config: object, version: int) -> dict:
    return {'provider':config.provider,'model':config.model,'base_url':config.base_url,
            'params':config.params,'timeout':config.timeout,'pipeline_version':f'corpus-v{version}'}


def _runtime_compatible(current: dict, saved: dict) -> bool:
    return ({k: v for k, v in current.items() if k != 'timeout'}
            == {k: v for k, v in saved.items() if k != 'timeout'})


def minimum_structure_calls(spans: list[dict], version: int) -> int:
    domains=domains_for(version)
    roster_windows=len({s['unit_id'] for s in spans}) if 'cast_roster' in domains else 0
    return 2*len(spans)+1+len(domains)+max(0,roster_windows-1)


def options_for(raw: dict, *, extent: dict, minimum: int, kind: str = 'structure') -> dict:
    allowed_keys = {'extent','note','chunk_chars','max_calls','max_input_chars','thread_ids','retry_failed',
                    'sample_mode','sample_count','chapter_start','chapter_end','tracks','auto_approve'}
    if not isinstance(raw,dict) or set(raw)-allowed_keys:
        raise ValueError('多层拆解参数无效')
    default_chunk = 8000 if kind == 'targeted' else 6000
    default_calls = 24 if kind == 'targeted' else 128
    result={'extent':raw.get('extent',extent.get('status','unknown')),'note':raw.get('note',extent.get('note','')),
        'chunk_chars':raw.get('chunk_chars',default_chunk),'max_calls':raw.get('max_calls',default_calls),
        'max_input_chars':raw.get('max_input_chars',64000),'thread_ids':raw.get('thread_ids',[]),
        'retry_failed':raw.get('retry_failed',False)}
    for name,lo,hi in (('chunk_chars',1000,20000),('max_calls',1,30000),('max_input_chars',8000,512000)):
        if type(result[name]) is not int or not lo<=result[name]<=hi:raise ValueError(f'{name}须在{lo}–{hi}之间')
    if result['extent'] not in ('complete','excerpt','unknown') or not isinstance(result['note'],str) or not result['note'].strip() or len(result['note'])>4000:
        raise ValueError('请确认参考文本完整性并填写依据；未知也须明确说明')
    if type(result['retry_failed']) is not bool:raise ValueError('重试必须明确选择')
    if not isinstance(result['thread_ids'],list) or any(not isinstance(v,str) for v in result['thread_ids']) or len(set(result['thread_ids']))!=len(result['thread_ids']) or len(result['thread_ids'])>20:
        raise ValueError('每次请明确选择最多20条线索/弧光，可分批提炼')
    if kind == 'targeted' or any(k in raw for k in ('sample_mode','sample_count','chapter_start','chapter_end','tracks','auto_approve')):
        sample_mode = raw.get('sample_mode', 'key_chapters')
        if sample_mode not in ('key_chapters', 'chapter_range', 'all_chapters'):
            raise ValueError('抽样范围须为 key_chapters / chapter_range / all_chapters')
        sample_count = raw.get('sample_count', 6)
        if type(sample_count) is not int or not 1 <= sample_count <= 20:
            raise ValueError('核心抽样章数须在 1–20 之间')
        ch_start = raw.get('chapter_start')
        ch_end = raw.get('chapter_end')
        for label, val in (('起始章号', ch_start), ('结束章号', ch_end)):
            if val is not None and (type(val) is not int or val < 1):
                raise ValueError(f'{label}须为正整数')
        raw_tracks = raw.get('tracks', list(DEFAULT_TRACK_IDS))
        if (not isinstance(raw_tracks, list) or not raw_tracks
                or any(not isinstance(t, str) or t not in TARGETED_TRACKS for t in raw_tracks)
                or len(set(raw_tracks)) != len(raw_tracks)):
            raise ValueError('请选择至少 1 个有效的精准步骤拆解维度')
        auto_approve = raw.get('auto_approve', True)
        if type(auto_approve) is not bool:
            raise ValueError('自动核验入库开关须为布尔值')
        result.update(
            sample_mode=sample_mode,
            sample_count=sample_count,
            chapter_start=ch_start,
            chapter_end=ch_end,
            tracks=list(raw_tracks),
            auto_approve=auto_approve,
        )
    if result['max_calls']<minimum:raise ValueError(f'调用上限低于已知最低需求{minimum}次；尚未请求模型')
    return result


class CorpusJobsMixin:
    def estimate_corpus(self,book_id: str,request: dict) -> dict:
        book=self._staging_row(book_id);content=self._book_text(book);current=self.get_corpus(book_id)
        raw=dict(request);raw.setdefault('note',current['body']['source_extent']['note'] or '等待作者确认完整性')
        kind=str(raw.pop('kind', 'structure'))
        options=options_for(raw,extent=current['body']['source_extent'],minimum=0,kind=kind if kind in ('structure','targeted') else 'structure')
        spans=source_spans(current['body']['units'],options['chunk_chars'])
        minimum=minimum_structure_calls(spans,SCHEMA_VERSION)
        targeted = estimate_targeted_calls(
            current['body']['units'], content,
            sample_mode=options.get('sample_mode', 'key_chapters'),
            sample_count=options.get('sample_count', 6),
            chapter_start=options.get('chapter_start'),
            chapter_end=options.get('chapter_end'),
            chunk_chars=options['chunk_chars'],
            tracks=options.get('tracks'),
        )
        return {'book_id':book_id,'characters':len(content),'chapter_units':len({s['unit_id'] for s in spans}),
            'source_spans':len(spans),'minimum_structure_calls':minimum,
            'targeted': targeted,
            'note':'最低次数不含长文本额外整合批次或重试；每次发送前仍受调用/字符预算限制。',
            'source_extent':current['body']['source_extent'],'options':options}

    def list_corpus_jobs(self,book_id: str) -> dict:
        self._staging_row(book_id)
        with self.connect() as conn:
            rows=conn.execute('SELECT id,kind,status,control,phase,error,base_version,created_at,updated_at FROM corpus_jobs WHERE book_id=? ORDER BY created_at DESC',(book_id,)).fetchall()
        return {'jobs':[dict(r) for r in rows]}

    def get_corpus_job(self,book_id: str,ident: str) -> dict:
        with self.connect() as conn:
            row=conn.execute('SELECT * FROM corpus_jobs WHERE id=? AND book_id=?',(ident,book_id)).fetchone()
            if not row:raise FileNotFoundError('多层拆解任务不存在')
            calls=[dict(r) for r in conn.execute('SELECT seq,call_key,phase,status,error,created_at,updated_at FROM corpus_calls WHERE job_id=? ORDER BY seq',(ident,))]
        result=dict(row);state=json.loads(result.pop('state_json'));result['options']=json.loads(result.pop('options_json'))
        result['runtime']=json.loads(result.pop('runtime_json'));result['calls']=calls
        result['structure_schema_version']=state['document'].get('schema_version',1)
        result['progress']={k:state.get(k) for k in ('survey_cursor','overview_cursor','detail_cursor','domain_index','relation_cursor','method_cursor','extract_cursor','synthesis_done','published_version','published_methods','published_voice_fingerprint','published_craft_fingerprints')}
        result['coverage']=state.get('coverage',{});result['calls_used']=len(calls)
        return result

    def corpus_call_record(self,book_id: str,ident: str,seq: int) -> dict:
        self.get_corpus_job(book_id,ident)
        with self.connect() as conn:row=conn.execute('SELECT * FROM corpus_calls WHERE job_id=? AND seq=?',(ident,seq)).fetchone()
        if not row:raise FileNotFoundError('调用记录不存在')
        return {'record':dict(row),'input':json.loads(artifact(self,row['input_path']).read_text(encoding='utf-8')),
            'output':json.loads(artifact(self,row['output_path']).read_text(encoding='utf-8')) if artifact(self,row['output_path']).is_file() else None}

    def _corpus_runtime(self) -> tuple:
        if self.config_path is None:raise ConfigRequired('CONFIG_REQUIRED: 请配置真实API，或使用人工结构分析')
        try:
            config=load_config(self.config_path);provider=make_provider(config)
            config,provider=resolve_stage_runtime(config,provider,'decompose')
        except ConfigRequired as exc:raise ConfigRequired('CONFIG_REQUIRED: '+str(exc)) from exc
        if provider.name=='fake':raise ConfigRequired('CONFIG_REQUIRED: 正式多层拆解不接受fake模型')
        # Reasoning/structured-JSON models routinely exceed 120s on long chapters; enforce a safe floor.
        if getattr(config, 'timeout', 0) < DECOMPOSE_MIN_TIMEOUT:
            config = replace(config, timeout=DECOMPOSE_MIN_TIMEOUT)
            provider = make_provider(config)
        return config,provider

    def start_corpus_job(self,book_id: str,request: dict) -> dict:
        config,provider=self._corpus_runtime()
        kind=request.get('kind','structure')
        if set(request)-{'kind','options'} or kind not in ('structure','methods','targeted'):raise ValueError('未知多层拆解任务')
        book=self._staging_row(book_id)
        if book['status'] in ('pending_review','rejected','decomposing'):raise ValueError('请先确认作品类型、等待当前任务结束，且不要使用已撤回作品')
        current=self.get_corpus(book_id);raw=request.get('options',{})
        options=options_for(raw,extent=current['body']['source_extent'],minimum=0,kind=kind)
        content=self._book_text(book)
        body=empty_document(content,options['extent'],options['note'])
        body['units']=[u for u in current['body']['units'] if u['level']!='scene']
        unit_errors=[i['message'] for i in graph_issues(body,len(content)) if i['field']=='units' and i['severity']=='error']
        if unit_errors:raise ValueError('请先修正章节目录：'+'；'.join(unit_errors[:8]))
        base=current['latest_version']
        if kind=='targeted':
            spans, paratext, total_story = select_targeted_spans(
                body['units'], content,
                sample_mode=options.get('sample_mode', 'key_chapters'),
                sample_count=options.get('sample_count', 6),
                chapter_start=options.get('chapter_start'),
                chapter_end=options.get('chapter_end'),
                chunk_chars=options['chunk_chars'],
            )
            minimum = len(spans) + 1
            state = {
                'document': body,
                'spans': spans,
                'skipped_paratext': [u['id'] for u in paratext],
                'total_story_chapters': total_story,
                'coverage': {'targeted_mode': True, 'survey_ranges': [], 'detail_ranges': [], 'reviewed_units': []},
                'extract_cursor': 0,
                'extracted': [],
                'synthesis': None,
                'synthesis_done': False,
            }
        else:
            spans=source_spans(body['units'],options['chunk_chars'])
            minimum=minimum_structure_calls(spans,body['schema_version'])
            state={'document':body,'spans':spans,'passage_observations':body['schema_version']>=5,
                   'craft_observations':body['schema_version']>=5,
                   'survey_contract_from':0,
                   'coverage':{'survey_ranges':[],'detail_ranges':[],'reviewed_units':[]},
                   'survey_cursor':0,'overview_cursor':0,'detail_cursor':0,'domain_index':0,'relation_cursor':0,'method_cursor':0,'candidates':[]}
        if kind=='methods':
            base=current['approved_version']
            if base is None:raise ValueError('请先审核全书结构，再提炼方法')
            approved=self.get_corpus(book_id,base)
            require_current_schema(approved['body'].get('schema_version', 1))
            if not approved['available']:raise ValueError('当前批准结构来源或完整性检查未通过')
            ids={t['id'] for t in approved['body']['threads']}
            selected=options['thread_ids']
            if not selected or len(selected)>20 or not set(selected)<=ids:raise ValueError('请选择1–20条已批准结构中的线索/弧光')
            options['thread_ids']=selected;state['document']=approved['body'];minimum=len(selected)
        options_for(options,extent=body['source_extent'],minimum=minimum,kind=kind)
        ident=uuid4().hex
        initial_phase = 'methods' if kind=='methods' else ('extract' if kind=='targeted' else 'survey')
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            active=conn.execute("SELECT id FROM corpus_jobs WHERE book_id=? AND status IN ('pending','running','paused','failed')",(book_id,)).fetchone()
            if active:raise ValueError('该作品已有未结束任务，请续接或取消后再开始')
            now=timestamp()
            conn.execute('INSERT INTO corpus_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (ident,book_id,kind,'pending','',initial_phase,book['sha256'],base,
                 encode(options),encode(runtime_profile(config,state['document']['schema_version'])),encode(state),'',book['status'],now,now))
        try:self._launch_corpus(book_id,ident,config,provider)
        except Exception:
            with self.connect() as conn:conn.execute("UPDATE corpus_jobs SET status='failed',error=?,updated_at=? WHERE id=?",('任务未能启动，未请求模型',timestamp(),ident))
            raise
        return self.get_corpus_job(book_id,ident)

    def _launch_corpus(self,book_id: str,ident: str,config: object,provider: object) -> None:
        with self._task_lock:
            lock=execution_lock(SimpleNamespace(directory=self.root),f'decompose:{book_id}')
            if not lock.__enter__():
                lock.__exit__(None,None,None)
                if any(t.is_alive() for t in self._tasks.values()):
                    raise ValueError('当前作品的上一个后台任务正在退出，请稍候再试')
                raise ValueError('另一个客户端正在处理此作品')
            original_status=None
            try:
                with self.connect() as conn:
                    conn.execute('BEGIN IMMEDIATE')
                    job=conn.execute('SELECT * FROM corpus_jobs WHERE id=?',(ident,)).fetchone()
                    if job['status'] not in ('pending','paused','failed'):raise ValueError('任务不能重复启动')
                    original_status=job['original_book_status']
                    conn.execute("UPDATE corpus_jobs SET status='running',control='',error='',updated_at=? WHERE id=?",(timestamp(),ident))
                    conn.execute("UPDATE staging_books SET status='decomposing',error='',updated_at=? WHERE id=? AND status NOT IN ('rejected','archived')",(timestamp(),book_id))
                from nw.studio.corpus_pipeline import run_job
                def worker() -> None:
                    try:run_job(self,ident,config,provider)
                    finally:
                        lock.__exit__(None,None,None)
                        with self._task_lock:self._tasks.pop(ident,None)
                thread=threading.Thread(target=worker,daemon=True,name='corpus-'+ident[:8]);self._tasks[ident]=thread;thread.start()
            except Exception as exc:
                lock.__exit__(None,None,None);self._tasks.pop(ident,None)
                if original_status is not None:
                    with self.connect() as conn:
                        conn.execute("UPDATE corpus_jobs SET status='failed',error=?,control='',updated_at=? WHERE id=? AND status='running'",
                                     (str(exc)[:4000],timestamp(),ident))
                        conn.execute("UPDATE staging_books SET status=?,updated_at=? WHERE id=? AND status='decomposing'",
                                     (original_status,timestamp(),book_id))
                raise

    def control_corpus_job(self,book_id: str,ident: str,request: dict) -> dict:
        action=request.get('action');job=self.get_corpus_job(book_id,ident)
        if action in ('pause','cancel'):
            if job['status'] not in ACTIVE:raise ValueError('该任务已结束')
            worker=self._tasks.get(ident) if action=='cancel' else None
            with self.connect() as conn:
                conn.execute('BEGIN IMMEDIATE')
                current=conn.execute('SELECT status FROM corpus_jobs WHERE id=?',(ident,)).fetchone()
                if not current or current['status'] not in ACTIVE:raise ValueError('该任务已结束，结果和完成状态保留')
                if action=='cancel':
                    conn.execute("UPDATE corpus_jobs SET status='cancelled',control='cancel',updated_at=? WHERE id=?",(timestamp(),ident))
                    conn.execute("UPDATE staging_books SET status=?,updated_at=? WHERE id=? AND status='decomposing'",(job['original_book_status'],timestamp(),book_id))
                elif current['status']=='running':conn.execute("UPDATE corpus_jobs SET control='pause',updated_at=? WHERE id=?",(timestamp(),ident))
            if worker and worker.is_alive() and worker is not threading.current_thread():
                worker.join(timeout=2)
        elif action=='resume':
            if job['status'] not in ('paused','failed'):raise ValueError('只有已暂停/失败的任务可以续接')
            if not isinstance(request.get('options',{}),dict) or set(request.get('options',{}))-{'max_calls','max_input_chars'}:
                raise ValueError('续接只可调整调用上限和输入预算；其他分析参数改变须新建任务')
            config,provider=self._corpus_runtime()
            current_runtime=runtime_profile(config,job['structure_schema_version'])
            if not _runtime_compatible(current_runtime,job['runtime']):raise ValueError('模型配置已改变，请恢复原配置续接或取消后新建，不能混用结果')
            current=self.get_corpus(book_id)
            actual=current['approved_version'] if job['kind']=='methods' else current['latest_version']
            if actual!=job['base_version']:raise ValueError('拆解结构已修改，请取消旧任务后重建')
            options={**job['options'],**request.get('options',{}),'retry_failed':request.get('retry_failed',False)}
            validated=options_for(options,extent=current['body']['source_extent'],minimum=job['calls_used'],kind=job['kind'])
            with self.connect() as conn:conn.execute('UPDATE corpus_jobs SET options_json=?,runtime_json=? WHERE id=?',(encode(validated),encode(current_runtime),ident))
            self._launch_corpus(book_id,ident,config,provider)
        else:raise ValueError('未知任务操作')
        return self.get_corpus_job(book_id,ident)


def recover_corpus_jobs(service: object) -> None:
    with service.connect() as conn:rows=conn.execute("SELECT id,book_id,original_book_status FROM corpus_jobs WHERE status IN ('pending','running')").fetchall()
    for row in rows:
        with execution_lock(SimpleNamespace(directory=service.root),f'decompose:{row["book_id"]}') as acquired:
            if not acquired:continue
            with service.connect() as conn:
                conn.execute("UPDATE corpus_jobs SET status='paused',control='',error=?,updated_at=? WHERE id=? AND status IN ('pending','running')",('上次进程中断；已完成结果保留，未知调用须明确重试',timestamp(),row['id']))
                conn.execute("UPDATE staging_books SET status=?,updated_at=? WHERE id=? AND status='decomposing'",(row['original_book_status'],timestamp(),row['book_id']))
