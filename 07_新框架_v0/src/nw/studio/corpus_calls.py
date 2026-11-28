"""Durable model-call receipts, explicit retry and bounded input/call counts."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Callable

from nw.studio.library_util import encode, timestamp


_TRANSIENT_NETWORK_ERRORS = {'timeout', 'connection_lost', 'proxy_tunnel', 'transport'}
_TRANSIENT_HTTP_CODES = {408, 429, 500, 502, 503, 504}


def _diagnose_raw_failure(raw: dict) -> tuple[str, bool]:
    """Return (human-readable Chinese failure diagnosis, is_transient_transport_error)."""
    reason = str(raw.get('finish_reason') or 'error')
    inner = raw.get('raw') if isinstance(raw.get('raw'), dict) else {}
    net = str(inner.get('network_failure') or '')
    http_status = inner.get('http_status')
    if net == 'timeout':
        return '模型请求超时（请调大设置中的 timeout 或缩小每段字符数；已保存进度可直接续接）', True
    if net in ('dns', 'tls', 'connection_refused', 'connection_lost', 'proxy_tunnel', 'transport'):
        labels = {
            'dns': '域名解析失败',
            'tls': 'TLS/证书握手失败',
            'connection_refused': '接口拒绝连接',
            'connection_lost': '网络连接中途断开',
            'proxy_tunnel': '代理隧道连接失败',
            'transport': '网络传输异常',
        }
        return f'网络请求失败（{labels.get(net, net)}），请检查接口地址与网络状态', net in _TRANSIENT_NETWORK_ERRORS
    if isinstance(http_status, int):
        if http_status in (401, 403):
            return f'API 认证失败（HTTP {http_status}），请检查环境变量中的密钥配置', False
        if http_status == 429:
            return 'API 触发限流（HTTP 429），请稍后重试', True
        if http_status in _TRANSIENT_HTTP_CODES:
            return f'API 服务端临时错误（HTTP {http_status}），可重试', True
        return f'API 返回错误（HTTP {http_status}）', False
    if reason == 'truncated':
        return '模型输出被 max_tokens 截断，请增大 max_tokens 或缩小每段字符数', False
    if reason == 'refused':
        return '模型拒绝返回当前片段内容（refused）', False
    return '模型未完整返回：' + reason, False


def _strip_trailing_commas(text: str) -> str:
    return re.sub(r',\s*([}\]])', r'\1', text)


class PipelineStop(Exception):
    def __init__(self, message: str, status: str = 'paused') -> None:
        super().__init__(message);self.status=status


def check_control(service: object, job_id: str) -> dict:
    with service.connect() as conn:row=conn.execute('SELECT * FROM corpus_jobs WHERE id=?',(job_id,)).fetchone()
    if not row:raise FileNotFoundError('拆解任务不存在')
    if row['status']=='cancelled' or row['control']=='cancel':raise PipelineStop('任务已取消','cancelled')
    if row['control']=='pause':raise PipelineStop('任务已在当前调用后暂停')
    if row['status']!='running':raise PipelineStop('任务当前没有运行')
    source=service._staging_row(row['book_id'])
    if source['status']=='rejected' or source['sha256']!=row['source_sha256']:raise ValueError('参考作品已撤回或来源版本改变')
    service._book_text(source)
    return dict(row)


def artifact(service: object, name: str) -> Path:
    path=(service.root/name).resolve()
    if not path.is_relative_to(service.root.resolve()):raise ValueError('调用记录路径越界')
    return path


def _extract_json_text(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return cleaned
    if cleaned.startswith('```'):
        matched = re.match(r'^```[A-Za-z0-9_-]*\s*([\s\S]*?)\s*```$', cleaned)
        if matched:
            return matched.group(1).strip()
        if '\n' in cleaned:
            cleaned = cleaned.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        else:
            cleaned = re.sub(r'^```[A-Za-z0-9_-]*|```$', '', cleaned).strip()
        return cleaned
    fenced = re.search(r'```(?:json)?\s*(\{[\s\S]*\})\s*```', cleaned)
    if fenced:
        return fenced.group(1).strip()
    if not cleaned.startswith('{'):
        start = cleaned.find('{')
        end = cleaned.rfind('}')
        if 0 <= start < end:
            return cleaned[start:end + 1]
    return cleaned


def parse_result(raw: dict, validator: Callable) -> object:
    if raw.get('finish_reason')!='complete':
        detail, _ = _diagnose_raw_failure(raw)
        raise ValueError(detail)
    text=_extract_json_text(raw.get('text',''))
    try:
        parsed = json.loads(text)
    except ValueError:
        parsed = json.loads(_strip_trailing_commas(text))
    return validator(parsed)


def model_call(service: object, job_id: str, config: object, provider: object, *, key: str,
               phase: str, messages: list[dict], validator: Callable,
               auto_retry_transient: bool = False) -> tuple[object,int]:
    row=check_control(service,job_id);options=json.loads(row['options_json'])
    request={'job_id':job_id,'call_key':key,'phase':phase,'source_sha256':row['source_sha256'],
        'provider':config.provider,'model':config.model,'base_url':config.base_url,'params':config.params,'messages':messages}
    fingerprint=hashlib.sha256(encode(request).encode('utf-8')).hexdigest()
    with service.connect() as conn:
        prior=conn.execute('SELECT * FROM corpus_calls WHERE job_id=? AND call_key=? ORDER BY seq DESC LIMIT 1',(job_id,key)).fetchone()
    if prior and prior['status']=='completed':
        if prior['request_sha256']!=fingerprint:raise ValueError('已完成调用的输入发生变化，请新建任务，不能混用旧结果')
        return json.loads(prior['result_json']),prior['seq']
    if prior and prior['status']=='sending' and artifact(service,prior['output_path']).is_file():
        if prior['request_sha256']!=fingerprint:raise ValueError('中断调用的输入已变化')
        try:
            value=parse_result(json.loads(artifact(service,prior['output_path']).read_text(encoding='utf-8')),validator)
        except (ValueError,KeyError,TypeError,IndexError) as exc:
            with service.connect() as conn:conn.execute("UPDATE corpus_calls SET status='invalid',error=?,updated_at=? WHERE job_id=? AND seq=?",(str(exc),timestamp(),job_id,prior['seq']))
            raise ValueError('已保留的模型结果无效，须明确重试该调用') from exc
        with service.connect() as conn:conn.execute("UPDATE corpus_calls SET status='completed',result_json=?,error='',updated_at=? WHERE job_id=? AND seq=?",(encode(value),timestamp(),job_id,prior['seq']))
        return value,prior['seq']
    if prior and options.get('retry_failed') is not True:
        raise PipelineStop('此前调用失败或结果未知；请明确选择重试，可能重复计费')
    characters=sum(len(m['content']) for m in messages)
    if characters>options['max_input_chars']:
        path=service.root/'corpus_calls'/job_id/('blocked_'+fingerprint[:16]+'.input.json');path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():path.write_text(encode({**request,'characters':characters}),encoding='utf-8')
        raise PipelineStop(f'CONTEXT_TOO_LARGE: 完整消息{characters}字符，预算{options["max_input_chars"]}；未发送、未截断。请提高预算后续接')

    max_attempts = 3 if auto_retry_transient else 1
    for attempt in range(max_attempts):
        with service.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            total=conn.execute('SELECT COUNT(*) FROM corpus_calls WHERE job_id=?',(job_id,)).fetchone()[0]
            if total>=options['max_calls']:raise PipelineStop('CALL_LIMIT: 已达调用上限；可明确增加上限后续接')
            seq=total+1;folder=service.root/'corpus_calls'/job_id;folder.mkdir(parents=True,exist_ok=True)
            input_path=folder/f'{seq:05}.input.json';output_path=folder/f'{seq:05}.output.json'
            input_path.write_text(encode({**request,'characters':characters,'created_at':timestamp()}),encoding='utf-8')
            conn.execute('INSERT INTO corpus_calls VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                (job_id,seq,key,phase,'sending',fingerprint,str(input_path.relative_to(service.root)),str(output_path.relative_to(service.root)),None,'',timestamp(),timestamp()))
        try:
            response=provider.generate(messages,model=config.model,**config.params)
            raw=asdict(response)
        except Exception as exc:
            raw={'finish_reason':'error','error_type':type(exc).__name__,'text':''}
            output_path.write_text(encode(raw),encoding='utf-8')
            with service.connect() as conn:conn.execute("UPDATE corpus_calls SET status='unknown',error=?,updated_at=? WHERE job_id=? AND seq=?",('请求失败，返回结果/计费状态未知',timestamp(),job_id,seq))
            if attempt + 1 < max_attempts:
                check_control(service, job_id)
                time.sleep(min(2.0, 0.5 * (attempt + 1)))
                continue
            raise PipelineStop('模型请求失败，输入输出已保留；须明确重试，可能重复计费') from exc
        output_path.write_text(encode(raw),encoding='utf-8')
        try:
            value=parse_result(raw,validator)
        except (ValueError,KeyError,TypeError,IndexError) as exc:
            _, transient = _diagnose_raw_failure(raw) if raw.get('finish_reason') != 'complete' else ('', False)
            with service.connect() as conn:conn.execute("UPDATE corpus_calls SET status='invalid',error=?,updated_at=? WHERE job_id=? AND seq=?",(str(exc),timestamp(),job_id,seq))
            if transient and attempt + 1 < max_attempts:
                check_control(service, job_id)
                time.sleep(min(3.0, 1.0 * (attempt + 1)))
                continue
            raise ValueError('模型结果未通过验证：'+str(exc)) from exc
        with service.connect() as conn:conn.execute("UPDATE corpus_calls SET status='completed',result_json=?,error='',updated_at=? WHERE job_id=? AND seq=?",(encode(value),timestamp(),job_id,seq))
        return value,seq
    raise PipelineStop('模型调用重试耗尽，请稍后续接')
