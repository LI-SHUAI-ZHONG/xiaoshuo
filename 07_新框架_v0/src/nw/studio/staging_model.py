"""Optional real-model decomposition with complete request/output audit files."""
from __future__ import annotations

from dataclasses import asdict
import json
import threading
from types import SimpleNamespace
from uuid import uuid4

from nw.call_control import execution_lock
from nw.config import ConfigRequired, load_config, make_provider, resolve_stage_runtime
from nw.studio import catalog
from nw.studio.library_util import encode, timestamp


def recover_decompositions(service: object) -> None:
    """Only recover abandoned runs; the OS lock protects other live servers."""
    with service.connect() as conn:
        ids = [row[0] for row in conn.execute("SELECT id FROM staging_books WHERE status='decomposing'")]
    for ident in ids:
        with execution_lock(SimpleNamespace(directory=service.root), f'decompose:{ident}') as acquired:
            if acquired:
                with service.connect() as conn:
                    conn.execute("UPDATE staging_books SET status='queued',error=?,updated_at=? WHERE id=? AND status='decomposing'",
                                 ('上次拆解进程已中断；输入输出记录已保留，可重新开始模型拆解。', timestamp(), ident))


def _run_locked(service: object, ident: str, text: str, config: object, provider: object, lock: object) -> None:
    try:
        _run(service, ident, text, config, provider)
    finally:
        lock.__exit__(None, None, None)


def start_decomposition(service: object, ident: str) -> dict:
    with service._task_lock:
        row = service._staging_row(ident)
        if row['status'] != 'queued':
            raise ValueError('自动拆解只能从待拆解队列启动')
        if service.config_path is None:
            raise ConfigRequired('CONFIG_REQUIRED: 请先配置真实模型，或用人工证据标注提交拆解')
        try:
            cfg = load_config(service.config_path)
            provider = make_provider(cfg)
            cfg, provider = resolve_stage_runtime(cfg, provider, 'decompose')
        except ConfigRequired as exc:
            raise ConfigRequired(f'CONFIG_REQUIRED: {exc}') from None
        if provider.name == 'fake':
            raise ConfigRequired('CONFIG_REQUIRED: 正式预存库不接受 fake 模型')
        text = service._book_text(row)
        lock = execution_lock(SimpleNamespace(directory=service.root), f'decompose:{ident}')
        if not lock.__enter__():
            lock.__exit__(None, None, None)
            raise ValueError('另一个客户端正在拆解此书，请等待当前任务结束')
        try:
            with service.connect() as conn:
                conn.execute('BEGIN IMMEDIATE')
                if conn.execute('SELECT status FROM staging_books WHERE id=?', (ident,)).fetchone()[0] != 'queued':
                    raise ValueError('拆解任务状态已改变，请刷新后重试')
                conn.execute("UPDATE staging_books SET status='decomposing',progress=0,error='',updated_at=? WHERE id=?",
                             (timestamp(), ident))
            thread = threading.Thread(target=_run_locked, args=(service, ident, text, cfg, provider, lock), daemon=True,
                                      name=f'decompose-{ident[:8]}')
            service._tasks[ident] = thread
            thread.start()
        except Exception:
            lock.__exit__(None, None, None)
            service._tasks.pop(ident, None)
            with service.connect() as conn:
                conn.execute("UPDATE staging_books SET status='queued',error=?,updated_at=? WHERE id=? AND status='decomposing'",
                             ('拆解任务未能启动，请重试。', timestamp(), ident))
            raise
    return service._book(service._staging_row(ident))


def _run(service: object, ident: str, text: str, config: object, provider: object) -> None:
    folder = service.root / 'calls' / uuid4().hex
    folder.mkdir(parents=True)
    all_items = []
    seen = set()
    try:
        options = [{k: r[k] for k in ('key', 'name')} for r in catalog.option_map().values()
                   if r.get('selectable') is not False]
        system = (
            '你是小说资料拆解员。只输出 JSON 对象 {"items":[...]}。只提取当前摘录中有直接证据的可复用用法；'
            '不得编造情节、推荐计数、选项 ID 或原文。每项字段 slot、option_key、stages、usage_text、'
            'evidence:{quote}；quote 必须是当前摘录中的连续原文，长度 10–400 字。'
            '拆解叙述用法时，区分事件实际发生的先后与读者读到的先后。用usage_text具体交代哪件往事被概述或展开、'
            '谁在回忆、观察或推断，哪些话别人听得到，读者由此新明白什么，眼前的反应或交流如何继续推动故事。'
            '依摘录选取有依据的方面；人物相信的解释保留为其看法，未写出的原因或后续选择留待核实。'
            '拆结构或人物用法时，找出这次交流、发现或交接怎样改变具体的人，以及变化的前因；'
            '分清某人自称的身份、当场职责和在场人已获知的事实。局部摘录不证明全书初次登场或跨章收获已被用上。'
            '若无可靠条目则返回空 items。slot 只能是 ' + ','.join(catalog.SLOTS) + '。'
            'stages 从 type_selection,type_adaptation,world_design,character_design,static_relations,plot_design,'
            'event_design,action_design,scene_design,state_transition,state_propagation,anchor_design,'
            'expression_design,bind_scope 中选取。每段最多 30 条。选项表：' + encode(options))
        starts = list(range(0, len(text), 12000))
        for index, start in enumerate(starts):
            if service._staging_row(ident)['status'] != 'decomposing':
                return
            chunk = text[start:min(start + 12400, len(text))]
            messages = [{'role': 'system', 'content': system},
                        {'role': 'user', 'content': f'原文字符起点 {start}。本次原文如下：\n{chunk}'}]
            snapshot = {'book_id': ident, 'chunk_index': index, 'start': start,
                        'model': config.model, 'provider': config.provider, 'params': config.params,
                        'messages': messages, 'created_at': timestamp()}
            stem = folder / f'{index:05d}'
            stem.with_suffix('.input.json').write_text(encode(snapshot), encoding='utf-8')
            try:
                result = provider.generate(messages, model=config.model, **config.params)
            except Exception as exc:
                stem.with_suffix('.output.json').write_text(encode({'finish_reason': 'error', 'error': type(exc).__name__}), encoding='utf-8')
                raise ValueError('模型请求失败；完整输入已留档，可重试') from exc
            stem.with_suffix('.output.json').write_text(encode(asdict(result)), encoding='utf-8')
            if result.finish_reason != 'complete':
                raise ValueError(f'模型未完整返回：{result.finish_reason}；未批准任何条目')
            raw = result.text.strip()
            if raw.startswith('```'):
                raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()
            parsed = json.loads(raw)
            if not isinstance(parsed, dict) or not isinstance(parsed.get('items'), list):
                raise ValueError('模型未返回 items 列表')
            for item in parsed['items']:
                quote = item.get('evidence', {}).get('quote', '')
                local = chunk.find(quote) if quote else -1
                if local < 0:
                    raise ValueError('模型证据不在本次原文摘录中')
                item['evidence'] = {'quote': quote, 'start': start + local, 'end': start + local + len(quote)}
                validated = service._validate_item(service._staging_row(ident), item, text)
                key = (validated['slot'], validated['option_key'], validated['evidence']['start'], validated['usage_text'])
                if key not in seen:
                    all_items.append(validated)
                    seen.add(key)
            with service.connect() as conn:
                conn.execute("UPDATE staging_books SET progress=?,updated_at=? WHERE id=? AND status='decomposing'",
                             ((index + 1) / len(starts), timestamp(), ident))
        if not all_items:
            raise ValueError('模型未提取到有证据的用法，可重试或人工标注')
        # A book may contain >500 items; insertion remains atomic and validation is identical.
        if len(all_items) > 500:
            raise ValueError('本次拆解超过 500 条；结果已留档，请分批人工复核导入')
        service._insert_items(ident, all_items, origin='model')
    except Exception as exc:
        folder.joinpath('error.json').write_text(encode({'error': str(exc), 'ts': timestamp()}), encoding='utf-8')
        with service.connect() as conn:
            conn.execute("UPDATE staging_books SET status='queued',error=?,updated_at=? WHERE id=? AND status='decomposing'",
                         (str(exc), timestamp(), ident))
    finally:
        with service._task_lock:
            service._tasks.pop(ident, None)
