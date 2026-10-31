"""Compatible /v1/chat/completions adapter."""
from typing import Any

from nw.llm.base import GenResult
from nw.llm.transport import post


class OpenAICompatProvider:
    name = 'openai_compat'

    def __init__(self, base_url: str, api_key: str, timeout: float = 120) -> None:
        self.base_url, self.api_key, self.timeout = base_url.rstrip('/'), api_key, timeout

    def generate(self, messages: list[dict], **params: Any) -> GenResult:
        raw, error = post(self.base_url + '/chat/completions',
                          {**params, 'messages': messages, 'stream': False}, self.timeout, self.api_key)
        text, reason, usage = '', 'error', raw.get('usage', {})
        try:
            if not error:
                choice = raw['choices'][0]
                message = choice['message']
                content = message.get('content')
                text = content if isinstance(content, str) else ''
                reason = {'stop': 'complete', 'length': 'truncated', 'content_filter': 'refused'}.get(choice.get('finish_reason'), 'error')
                if message.get('refusal'):
                    reason = 'refused'
                elif reason == 'complete' and not text.strip():
                    reason = 'error'
        except (KeyError, IndexError, TypeError, AttributeError):
            reason = 'error'
        request_id = raw.get('id')
        if request_id is not None and not isinstance(request_id, str):
            request_id, reason = None, 'error'
        return GenResult(text, reason, usage if isinstance(usage, dict) else {}, request_id, raw)
