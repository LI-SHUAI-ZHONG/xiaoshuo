"""Ollama /api/chat adapter (stream=false)."""
from typing import Any

from nw.llm.base import GenResult
from nw.llm.transport import post


class OllamaProvider:
    name = 'ollama'

    def __init__(self, base_url: str, timeout: float = 120) -> None:
        self.base_url, self.timeout = base_url.rstrip('/'), timeout

    def generate(self, messages: list[dict], **params: Any) -> GenResult:
        model = params.pop('model')
        raw, error = post(self.base_url + '/api/chat',
                          {'model': model, 'messages': messages, 'stream': False, 'options': params}, self.timeout)
        text, reason = '', 'error'
        try:
            if not error:
                content = raw['message']['content']
                text = content if isinstance(content, str) else ''
                reason = {'stop': 'complete', 'length': 'truncated'}.get(raw.get('done_reason'), 'error')
                if raw.get('done') is False:
                    reason = 'truncated'
                elif raw.get('done') is not True:
                    reason = 'error'
                if reason == 'complete' and not text.strip():
                    reason = 'error'
        except (KeyError, TypeError):
            reason = 'error'
        usage = {k: raw[k] for k in ('prompt_eval_count', 'eval_count') if k in raw}
        return GenResult(text, reason, usage, None, raw)
