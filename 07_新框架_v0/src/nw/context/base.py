"""Auditable context packages. Project and scene are frozen JSON dictionaries."""
from dataclasses import dataclass
from typing import Protocol

@dataclass
class ContextItem:
    source: str
    text: str
    reason: str

@dataclass
class ContextPackage:
    items: list[ContextItem]
    token_estimate: int

class ContextProvider(Protocol):
    name: str
    def build(self, project: dict, scene: dict) -> ContextPackage: ...


def package(items: list[ContextItem]) -> ContextPackage:
    # Conservative character-based estimate, not a model-specific tokenizer.
    return ContextPackage(items, sum(len(i.text) for i in items))
