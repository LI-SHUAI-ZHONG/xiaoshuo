"""Null graph adapter for disabled or unconfigured extension deployments."""

from __future__ import annotations

from typing import TYPE_CHECKING

from accos.kernel.errors import InvalidStateError

if TYPE_CHECKING:
    from uuid import UUID

    from accos.kernel.graph import (
        GraphDirection,
        GraphEdge,
        GraphNodeRef,
        GraphProjectionEvent,
        GraphTraversal,
    )


class NullGraphStore:
    """Fail closed without implying that an empty graph is a real result."""

    configured = False

    async def neighbors(
        self,
        node: GraphNodeRef,
        *,
        projection_owner: str,
        direction: GraphDirection,
        limit: int,
    ) -> tuple[GraphEdge, ...]:
        del node, projection_owner, direction, limit
        raise InvalidStateError("The graph capability is not configured.")

    async def replace_edges(
        self,
        workspace_id: UUID,
        *,
        projection_owner: str,
        edges: tuple[GraphEdge, ...],
    ) -> None:
        del workspace_id, projection_owner, edges
        raise InvalidStateError("The graph capability is not configured.")

    async def drop_projection(self, workspace_id: UUID, *, projection_owner: str) -> None:
        del workspace_id, projection_owner
        raise InvalidStateError("The graph capability is not configured.")

    async def rebuild(
        self,
        workspace_id: UUID,
        *,
        projection_owner: str,
        events: tuple[GraphProjectionEvent, ...],
    ) -> None:
        del workspace_id, projection_owner, events
        raise InvalidStateError("The graph capability is not configured.")

    async def traverse(
        self,
        start: GraphNodeRef,
        *,
        projection_owner: str,
        direction: GraphDirection,
        max_depth: int,
        limit: int,
    ) -> GraphTraversal:
        del start, projection_owner, direction, max_depth, limit
        raise InvalidStateError("The graph capability is not configured.")
