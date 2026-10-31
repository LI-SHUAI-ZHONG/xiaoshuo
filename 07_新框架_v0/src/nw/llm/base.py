"""Model adapter contract."""
from dataclasses import dataclass
from typing import Any, Literal, Protocol


@dataclass
class GenResult:
    text: str
    finish_reason: Literal['complete', 'truncated', 'error', 'refused']
    usage: dict
    request_id: str | None
    raw: dict | None


class LLMProvider(Protocol):
    name: str

    def generate(self, messages: list[dict], **params: Any) -> GenResult: ...
