"""Programmable adapter for isolated automated tests only; never selected by CLI."""
from copy import deepcopy
from typing import Any

from nw.llm.base import GenResult


class FakeProvider:
    name = 'fake'

    def __init__(self, reason: str = 'complete', text: str = 'test output') -> None:
        if reason not in ('complete', 'truncated', 'error', 'refused'):
            raise ValueError('Invalid fake finish reason')
        self.reason, self.text = reason, '[FAKE] ' + text
        self.calls: list[list[dict]] = []

    def generate(self, messages: list[dict], **params: Any) -> GenResult:
        self.calls.append(deepcopy(messages))
        return GenResult(self.text, self.reason, {}, 'fake-request', {'test': True})
