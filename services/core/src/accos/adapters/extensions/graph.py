"""PostgreSQL disposable relationship projection for the graph extension."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Index, String, UniqueConstraint, Uuid, and_, delete, or_, select
from sqlalchemy.orm import Mapped, mapped_column

from accos.adapters.persistence.models import SCHEMA_NAME, Base
from accos.kernel.graph import (
    GraphDirection,
    GraphEdge,
    GraphNodeRef,
    GraphProjectionOperation,
    GraphTraversal,
)

if TYPE_CHECKING:
    from accos.adapters.persistence.database import AsyncSessionFactory
    from accos.kernel.graph import GraphProjectionEvent

_MAX_GRAPH_LIMIT = 1000
_MAX_GRAPH_DEPTH = 10


class ExtensionGraphNodeRow(Base):
    """Disposable node projection; authoritative records stay module-owned."""

    __tablename__ = "extension_graph_nodes"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    projection_owner: Mapped[str] = mapped_column(String(100), nullable=False)
    node_owner: Mapped[str] = mapped_column(String(100), nullable=False)
    node_kind: Mapped[str] = mapped_column(String(100), nullable=False)
    node_identifier: Mapped[UUID] = mapped_column(Uuid, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "projection_owner",
            "node_owner",
            "node_kind",
            "node_identifier",
            name="uq_extension_graph_node",
        ),
        Index(
            "ix_extension_graph_nodes_scope",
            "workspace_id",
            "projection_owner",
            "node_kind",
        ),
        {"schema": SCHEMA_NAME},
    )


class ExtensionGraphEdgeRow(Base):
    """Disposable directed edge projection."""

    __tablename__ = "extension_graph_edges"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    projection_owner: Mapped[str] = mapped_column(String(100), nullable=False)
    source_owner: Mapped[str] = mapped_column(String(100), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(100), nullable=False)
    source_identifier: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    target_owner: Mapped[str] = mapped_column(String(100), nullable=False)
    target_kind: Mapped[str] = mapped_column(String(100), nullable=False)
    target_identifier: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    relationship: Mapped[str] = mapped_column(String(100), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "projection_owner",
            "source_owner",
            "source_kind",
            "source_identifier",
            "target_owner",
            "target_kind",
            "target_identifier",
            "relationship",
            name="uq_extension_graph_edge",
        ),
        Index(
            "ix_extension_graph_edges_source",
            "workspace_id",
            "projection_owner",
            "source_identifier",
        ),
        Index(
            "ix_extension_graph_edges_target",
            "workspace_id",
            "projection_owner",
            "target_identifier",
        ),
        {"schema": SCHEMA_NAME},
    )


class SqlAlchemyExtensionGraphStore:
    """Rebuildable PostgreSQL projection with bounded in-process traversal."""

    configured = True

    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def neighbors(
        self,
        node: GraphNodeRef,
        *,
        projection_owner: str,
        direction: GraphDirection,
        limit: int,
    ) -> tuple[GraphEdge, ...]:
        _validate_bounds(limit=limit)
        scope = (
            ExtensionGraphEdgeRow.workspace_id == node.workspace_id,
            ExtensionGraphEdgeRow.projection_owner == projection_owner,
        )
        outgoing = and_(
            ExtensionGraphEdgeRow.source_owner == node.owner,
            ExtensionGraphEdgeRow.source_kind == node.kind,
            ExtensionGraphEdgeRow.source_identifier == node.identifier,
        )
        incoming = and_(
            ExtensionGraphEdgeRow.target_owner == node.owner,
            ExtensionGraphEdgeRow.target_kind == node.kind,
            ExtensionGraphEdgeRow.target_identifier == node.identifier,
        )
        if direction is GraphDirection.OUTGOING:
            direction_filter = outgoing
        elif direction is GraphDirection.INCOMING:
            direction_filter = incoming
        else:
            direction_filter = or_(outgoing, incoming)
        statement = (
            select(ExtensionGraphEdgeRow)
            .where(*scope, direction_filter)
            .order_by(
                ExtensionGraphEdgeRow.relationship,
                ExtensionGraphEdgeRow.source_identifier,
                ExtensionGraphEdgeRow.target_identifier,
            )
            .limit(limit)
        )
        async with self._sessions() as session:
            rows = (await session.scalars(statement)).all()
        return tuple(_edge_from_row(row) for row in rows)

    async def replace_edges(
        self,
        workspace_id: UUID,
        *,
        projection_owner: str,
        edges: tuple[GraphEdge, ...],
    ) -> None:
        _validate_edges(workspace_id, edges)
        unique_nodes = {
            _node_key(node): node for edge in edges for node in (edge.source, edge.target)
        }
        unique_edges = {_edge_key(edge): edge for edge in edges}
        async with self._sessions.begin() as session:
            await session.execute(
                delete(ExtensionGraphEdgeRow).where(
                    ExtensionGraphEdgeRow.workspace_id == workspace_id,
                    ExtensionGraphEdgeRow.projection_owner == projection_owner,
                )
            )
            await session.execute(
                delete(ExtensionGraphNodeRow).where(
                    ExtensionGraphNodeRow.workspace_id == workspace_id,
                    ExtensionGraphNodeRow.projection_owner == projection_owner,
                )
            )
            session.add_all(_node_row(projection_owner, node) for node in unique_nodes.values())
            session.add_all(_edge_row(projection_owner, edge) for edge in unique_edges.values())

    async def drop_projection(self, workspace_id: UUID, *, projection_owner: str) -> None:
        await self.replace_edges(workspace_id, projection_owner=projection_owner, edges=())

    async def rebuild(
        self,
        workspace_id: UUID,
        *,
        projection_owner: str,
        events: tuple[GraphProjectionEvent, ...],
    ) -> None:
        projected: dict[tuple[object, ...], GraphEdge] = {}
        for event in sorted(events, key=lambda item: (item.sequence, str(item.id))):
            if event.workspace_id != workspace_id or event.projection_owner != projection_owner:
                raise ValueError("graph rebuild event scope is inconsistent")
            _validate_edges(workspace_id, (event.edge,))
            key = _edge_key(event.edge)
            if event.operation is GraphProjectionOperation.UPSERT:
                projected[key] = event.edge
            else:
                projected.pop(key, None)
        await self.replace_edges(
            workspace_id,
            projection_owner=projection_owner,
            edges=tuple(projected.values()),
        )

    async def traverse(
        self,
        start: GraphNodeRef,
        *,
        projection_owner: str,
        direction: GraphDirection,
        max_depth: int,
        limit: int,
    ) -> GraphTraversal:
        _validate_bounds(limit=limit, max_depth=max_depth)
        visited = {_node_key(start): start}
        frontier: tuple[GraphNodeRef, ...] = (start,)
        selected: dict[tuple[object, ...], GraphEdge] = {}
        truncated = False
        for _depth in range(max_depth):
            next_frontier: dict[tuple[object, ...], GraphNodeRef] = {}
            for node in frontier:
                remaining = limit - len(selected)
                if remaining <= 0:
                    truncated = True
                    break
                for edge in await self.neighbors(
                    node,
                    projection_owner=projection_owner,
                    direction=direction,
                    limit=remaining,
                ):
                    selected[_edge_key(edge)] = edge
                    for candidate in (edge.source, edge.target):
                        key = _node_key(candidate)
                        if key not in visited:
                            visited[key] = candidate
                            next_frontier[key] = candidate
            if truncated or not next_frontier:
                break
            frontier = tuple(next_frontier.values())
        return GraphTraversal(
            start,
            tuple(visited.values()),
            tuple(selected.values()),
            truncated,
        )


def _validate_bounds(*, limit: int, max_depth: int | None = None) -> None:
    if not 1 <= limit <= _MAX_GRAPH_LIMIT:
        raise ValueError("graph limit must be between 1 and 1000")
    if max_depth is not None and not 1 <= max_depth <= _MAX_GRAPH_DEPTH:
        raise ValueError("graph max_depth must be between 1 and 10")


def _validate_edges(workspace_id: UUID, edges: tuple[GraphEdge, ...]) -> None:
    if any(
        edge.source.workspace_id != workspace_id or edge.target.workspace_id != workspace_id
        for edge in edges
    ):
        raise ValueError("graph edge scope is inconsistent")


def _node_key(node: GraphNodeRef) -> tuple[object, ...]:
    return node.owner, node.kind, node.identifier


def _edge_key(edge: GraphEdge) -> tuple[object, ...]:
    return (*_node_key(edge.source), *_node_key(edge.target), edge.relationship)


def _node_row(projection_owner: str, node: GraphNodeRef) -> ExtensionGraphNodeRow:
    return ExtensionGraphNodeRow(
        workspace_id=node.workspace_id,
        projection_owner=projection_owner,
        node_owner=node.owner,
        node_kind=node.kind,
        node_identifier=node.identifier,
    )


def _edge_row(projection_owner: str, edge: GraphEdge) -> ExtensionGraphEdgeRow:
    return ExtensionGraphEdgeRow(
        workspace_id=edge.source.workspace_id,
        projection_owner=projection_owner,
        source_owner=edge.source.owner,
        source_kind=edge.source.kind,
        source_identifier=edge.source.identifier,
        target_owner=edge.target.owner,
        target_kind=edge.target.kind,
        target_identifier=edge.target.identifier,
        relationship=edge.relationship,
    )


def _edge_from_row(row: ExtensionGraphEdgeRow) -> GraphEdge:
    return GraphEdge(
        GraphNodeRef(row.workspace_id, row.source_owner, row.source_kind, row.source_identifier),
        GraphNodeRef(row.workspace_id, row.target_owner, row.target_kind, row.target_identifier),
        row.relationship,
    )
