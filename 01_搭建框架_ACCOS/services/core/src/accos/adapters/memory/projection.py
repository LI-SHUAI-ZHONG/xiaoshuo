"""Disposable Working/Session cache projection adapters."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from uuid import UUID

from redis.asyncio import Redis

if TYPE_CHECKING:
    from accos.modules.memory.domain import MemoryRecord


class InMemoryMemoryProjection:
    """Redis-like disposable projection used to prove loss and rebuild semantics."""

    def __init__(self) -> None:
        self._records: dict[tuple[UUID, UUID], tuple[UUID, ...]] = {}

    async def replace(
        self, workspace_id: UUID, project_id: UUID, records: tuple[MemoryRecord, ...]
    ) -> None:
        self._records[(workspace_id, project_id)] = tuple(record.id for record in records)

    async def load(self, workspace_id: UUID, project_id: UUID) -> tuple[UUID, ...]:
        return self._records.get((workspace_id, project_id), ())

    async def clear(self, workspace_id: UUID, project_id: UUID) -> None:
        self._records.pop((workspace_id, project_id), None)


class RedisMemoryProjection:
    """Disposable Redis index containing record ids only, never source-of-truth facts."""

    def __init__(
        self,
        redis_url: str,
        *,
        ttl_seconds: int = 3600,
        timeout_seconds: float = 5.0,
    ) -> None:
        if ttl_seconds < 1 or timeout_seconds <= 0:
            raise ValueError("memory projection TTL and timeout must be positive")
        self._redis_url = redis_url
        self._ttl_seconds = ttl_seconds
        self._timeout_seconds = timeout_seconds

    async def replace(
        self, workspace_id: UUID, project_id: UUID, records: tuple[MemoryRecord, ...]
    ) -> None:
        client = self._client()
        try:
            await client.set(
                _key(workspace_id, project_id),
                json.dumps([str(record.id) for record in records]),
                ex=self._ttl_seconds,
            )
        finally:
            await client.aclose()

    async def load(self, workspace_id: UUID, project_id: UUID) -> tuple[UUID, ...]:
        client = self._client()
        try:
            payload = await client.get(_key(workspace_id, project_id))
            return () if payload is None else tuple(UUID(item) for item in json.loads(payload))
        finally:
            await client.aclose()

    async def clear(self, workspace_id: UUID, project_id: UUID) -> None:
        client = self._client()
        try:
            await client.delete(_key(workspace_id, project_id))
        finally:
            await client.aclose()

    def _client(self) -> Redis:
        return Redis.from_url(
            self._redis_url,
            decode_responses=True,
            socket_connect_timeout=self._timeout_seconds,
            socket_timeout=self._timeout_seconds,
        )


def _key(workspace_id: UUID, project_id: UUID) -> str:
    return f"accos:memory-projection:{workspace_id}:{project_id}"
