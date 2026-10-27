"""Graph relationship port without a dedicated graph database dependency."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from uuid import UUID


@dataclass(frozen=True, slots=True)
class GraphNodeRef:
    """Stable reference to a module-owned record."""

    workspace_id: UUID
    owner: str
    kind: str
    identifier: UUID


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """Portable relationship representation for a future adapter."""

    source: GraphNodeRef
    target: GraphNodeRef
    relationship: str


class GraphDirection(StrEnum):
    """Bounded traversal direction."""

    INCOMING = "incoming"
    OUTGOING = "outgoing"
    BOTH = "both"


class GraphProjectionOperation(StrEnum):
    """Replayable change from an authoritative event stream."""

    UPSERT = "upsert"
    REMOVE = "remove"


@dataclass(frozen=True, slots=True)
class GraphProjectionEvent:
    """Ordered event consumed to rebuild a disposable relation projection."""

    id: UUID
    sequence: int
    workspace_id: UUID
    projection_owner: str
    operation: GraphProjectionOperation
    edge: GraphEdge


@dataclass(frozen=True, slots=True)
class GraphTraversal:
    """Bounded projection result; it is never an authoritative domain record."""

    start: GraphNodeRef
    nodes: tuple[GraphNodeRef, ...]
    edges: tuple[GraphEdge, ...]
    truncated: bool


class GraphStore(Protocol):
    """Disposable graph projection and bounded traversal boundary."""

    configured: bool

    async def neighbors(
        self,
        node: GraphNodeRef,
        *,
        projection_owner: str,
        direction: GraphDirection,
        limit: int,
    ) -> tuple[GraphEdge, ...]:
        """Read bounded neighboring relationships in the same workspace."""
        ...

    async def replace_edges(
        self,
        workspace_id: UUID,
        *,
        projection_owner: str,
        edges: tuple[GraphEdge, ...],
    ) -> None:
        """Replace one owner's projected edges through an explicit port."""
        ...

    async def drop_projection(self, workspace_id: UUID, *, projection_owner: str) -> None:
        """Delete only disposable projection rows for one owner."""
        ...

    async def rebuild(
        self,
        workspace_id: UUID,
        *,
        projection_owner: str,
        events: tuple[GraphProjectionEvent, ...],
    ) -> None:
        """Rebuild the projection exclusively from ordered authoritative events."""
        ...

    async def traverse(
        self,
        start: GraphNodeRef,
        *,
        projection_owner: str,
        direction: GraphDirection,
        max_depth: int,
        limit: int,
    ) -> GraphTraversal:
        """Traverse a bounded number of projected edges."""
        ...
