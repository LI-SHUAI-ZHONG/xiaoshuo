"""Ports owned by the memory module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from accos.modules.memory.domain import (
        AllowedAnchor,
        CompressionDraft,
        ContextPackage,
        MemoryConflict,
        MemoryGrant,
        MemoryLink,
        MemoryRecord,
        MemoryScope,
        RankedMemory,
        RetentionEvaluation,
    )


class MemoryWriter(Protocol):
    async def add(self, record: MemoryRecord, links: tuple[MemoryLink, ...] = ()) -> None: ...


class MemoryRetriever(Protocol):
    async def retrieve(
        self,
        allowed_anchors: tuple[AllowedAnchor, ...],
        scopes: frozenset[MemoryScope],
        memory_types: frozenset[str],
    ) -> tuple[MemoryRecord, ...]: ...


class MemoryRanker(Protocol):
    def rank(
        self, records: tuple[MemoryRecord, ...], now: datetime
    ) -> tuple[tuple[RankedMemory, ...], tuple[tuple[MemoryRecord, str], ...]]: ...


class MemoryCompressor(Protocol):
    def compress(
        self, records: tuple[MemoryRecord, ...], budget_chars: int
    ) -> CompressionDraft: ...


class RetentionPolicy(Protocol):
    def evaluate(self, record: MemoryRecord, now: datetime) -> RetentionEvaluation: ...


class ConflictResolver(Protocol):
    def candidate_resolutions(
        self, current: MemoryRecord, candidate: MemoryRecord
    ) -> tuple[str, ...]: ...


class MemoryRepository(MemoryWriter, MemoryRetriever, Protocol):
    async def get_record(self, workspace_id: UUID, record_id: UUID) -> MemoryRecord | None: ...

    async def add_grant(self, grant: MemoryGrant) -> None: ...

    async def grants_for(self, workspace_id: UUID, project_id: UUID) -> tuple[MemoryGrant, ...]: ...

    async def add_conflict(self, candidate: MemoryRecord, conflict: MemoryConflict) -> None: ...

    async def get_conflict(
        self, workspace_id: UUID, conflict_id: UUID
    ) -> MemoryConflict | None: ...

    async def decide_conflict(
        self,
        workspace_id: UUID,
        conflict_id: UUID,
        *,
        accepted: bool,
        decided_by: UUID,
        decided_at: datetime,
    ) -> MemoryConflict: ...

    async def archive(
        self, workspace_id: UUID, record_id: UUID, *, actor_id: UUID, archived_at: datetime
    ) -> MemoryRecord: ...

    async def save_package(self, package: ContextPackage) -> None: ...

    async def get_package(
        self, workspace_id: UUID, project_id: UUID, package_id: UUID
    ) -> ContextPackage | None: ...


class ContextPackageReader(Protocol):
    async def get_package(
        self, workspace_id: UUID, project_id: UUID, package_id: UUID
    ) -> ContextPackage | None: ...


class MemoryProjection(Protocol):
    async def replace(
        self, workspace_id: UUID, project_id: UUID, records: tuple[MemoryRecord, ...]
    ) -> None: ...

    async def load(self, workspace_id: UUID, project_id: UUID) -> tuple[UUID, ...]: ...

    async def clear(self, workspace_id: UUID, project_id: UUID) -> None: ...
