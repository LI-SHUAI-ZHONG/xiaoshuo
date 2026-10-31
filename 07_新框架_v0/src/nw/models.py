"""B2 persisted records. JSON fields contain serialized JSON text."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Project:
    id: str
    name: str
    created_at: str


@dataclass(frozen=True)
class Brief:
    project_id: str
    text: str
    constraints: str
    version: int


@dataclass(frozen=True)
class BibleEntry:
    project_id: str
    kind: Literal['world', 'character', 'style', 'taboo']
    name: str
    body: str
    version: int


@dataclass(frozen=True)
class Chapter:
    id: str
    project_id: str
    index: int
    title: str


@dataclass(frozen=True)
class Scene:
    id: str
    chapter_id: str
    index: int
    card_json: str


@dataclass(frozen=True)
class Draft:
    id: str
    scene_id: str
    version: int
    text: str
    status: Literal['partial', 'complete', 'truncated', 'error']
    run_id: str
    created_at: str


@dataclass(frozen=True)
class Accepted:
    scene_id: str
    draft_id: str
    accepted_at: str


@dataclass(frozen=True)
class Run:
    id: str
    scene_id: str
    kind: Literal['write', 'review', 'revise']
    provider: str
    model: str
    params_json: str
    input_snapshot_json: str
    context_package_json: str
    output_text: str
    finish_reason: str
    usage_json: str
    started_at: str
    ended_at: str


@dataclass(frozen=True)
class StateNote:
    scene_id: str
    kind: Literal['character_state', 'foreshadow', 'fact']
    text: str
