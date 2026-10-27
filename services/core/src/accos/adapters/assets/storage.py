"""MinIO/S3 and deterministic in-memory object-storage adapters."""

from __future__ import annotations

import asyncio
import hashlib
from io import BytesIO
from typing import TYPE_CHECKING, TypeVar
from urllib.parse import urlsplit

from minio import Minio
from minio.error import S3Error
from urllib3 import PoolManager, Timeout

from accos.modules.assets.ports import StoredObject

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from minio.datatypes import Object

    from accos.kernel.observability import TelemetryRuntime
    from accos.kernel.resilience import ResilienceExecutor
    from accos.modules.assets.ports import ObjectStorage

T = TypeVar("T")


def validate_object_key(object_key: str) -> None:
    """Reject path-like or non-canonical object keys at every adapter boundary."""
    parts = object_key.split("/")
    if (
        not object_key
        or object_key.startswith("/")
        or "\\" in object_key
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise ValueError("object key must be a canonical service-generated key")


class InMemoryObjectStorage:
    """Integrity-enforcing fake for application and contract tests."""

    def __init__(self) -> None:
        self._objects: dict[str, tuple[bytes, StoredObject]] = {}

    async def put(
        self,
        object_key: str,
        data: bytes,
        *,
        media_type: str,
        content_hash: str,
    ) -> StoredObject:
        validate_object_key(object_key)
        if hashlib.sha256(data).hexdigest() != content_hash:
            raise ValueError("object content hash does not match")
        metadata = StoredObject(object_key, content_hash, media_type, len(data))
        existing = self._objects.get(object_key)
        if existing is not None and existing != (data, metadata):
            raise ValueError("object key already contains different content")
        self._objects[object_key] = (bytes(data), metadata)
        return metadata

    async def get(self, object_key: str) -> bytes:
        validate_object_key(object_key)
        try:
            return self._objects[object_key][0]
        except KeyError as error:
            raise FileNotFoundError(object_key) from error

    async def stat(self, object_key: str) -> StoredObject | None:
        validate_object_key(object_key)
        value = self._objects.get(object_key)
        return None if value is None else value[1]

    def simulate_missing(self, object_key: str) -> None:
        """Drop one fake object to exercise reconciliation without production deletion APIs."""
        self._objects.pop(object_key, None)

    async def delete_orphan(self, object_key: str) -> None:
        validate_object_key(object_key)
        self._objects.pop(object_key, None)

    def simulate_corruption(self, object_key: str, data: bytes) -> None:
        """Alter fake bytes while retaining metadata for integrity tests."""
        metadata = self._objects[object_key][1]
        self._objects[object_key] = (data, metadata)


class MinioObjectStorage:
    """S3-compatible object adapter configured for MinIO or another S3 endpoint."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        endpoint: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        secure: bool,
        region: str,
        timeout_seconds: float = 5.0,
    ) -> None:
        parsed = urlsplit(endpoint)
        if parsed.hostname is None or timeout_seconds <= 0:
            raise ValueError("object storage endpoint and timeout are invalid")
        authority = parsed.netloc
        self._bucket = bucket
        self._client = Minio(
            authority,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
            region=region,
            http_client=PoolManager(
                timeout=Timeout(connect=timeout_seconds, read=timeout_seconds),
                retries=False,
            ),
        )

    async def put(
        self,
        object_key: str,
        data: bytes,
        *,
        media_type: str,
        content_hash: str,
    ) -> StoredObject:
        validate_object_key(object_key)
        if hashlib.sha256(data).hexdigest() != content_hash:
            raise ValueError("object content hash does not match")
        await asyncio.to_thread(
            self._client.put_object,
            self._bucket,
            object_key,
            BytesIO(data),
            len(data),
            content_type=media_type,
            metadata={"sha256": content_hash},
        )
        return StoredObject(object_key, content_hash, media_type, len(data))

    async def get(self, object_key: str) -> bytes:
        validate_object_key(object_key)

        def read() -> bytes:
            response = self._client.get_object(self._bucket, object_key)
            try:
                return bytes(response.read())
            finally:
                response.close()
                response.release_conn()

        try:
            return await asyncio.to_thread(read)
        except S3Error as error:
            if error.code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
                raise FileNotFoundError(object_key) from error
            raise

    async def stat(self, object_key: str) -> StoredObject | None:
        validate_object_key(object_key)
        try:
            value = await asyncio.to_thread(self._client.stat_object, self._bucket, object_key)
        except S3Error as error:
            if error.code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
                return None
            raise
        return _stored_object(object_key, value)

    async def delete_orphan(self, object_key: str) -> None:
        validate_object_key(object_key)
        await asyncio.to_thread(self._client.remove_object, self._bucket, object_key)


class ResilientObjectStorage:
    """Apply shared resilience and safe metrics to the concrete object adapter."""

    def __init__(
        self,
        storage: ObjectStorage,
        resilience: ResilienceExecutor,
        telemetry: TelemetryRuntime,
    ) -> None:
        self._storage = storage
        self._resilience = resilience
        self._telemetry = telemetry

    async def put(
        self,
        object_key: str,
        data: bytes,
        *,
        media_type: str,
        content_hash: str,
    ) -> StoredObject:
        async def invoke() -> StoredObject:
            return await self._storage.put(
                object_key,
                data,
                media_type=media_type,
                content_hash=content_hash,
            )

        return await self._call("put", invoke)

    async def get(self, object_key: str) -> bytes:
        async def invoke() -> bytes:
            return await self._storage.get(object_key)

        return await self._call("get", invoke)

    async def stat(self, object_key: str) -> StoredObject | None:
        async def invoke() -> StoredObject | None:
            return await self._storage.stat(object_key)

        return await self._call("stat", invoke)

    async def delete_orphan(self, object_key: str) -> None:
        async def invoke() -> None:
            await self._storage.delete_orphan(object_key)

        await self._call("delete_orphan", invoke)

    async def _call(self, operation: str, invoke: Callable[[], Awaitable[T]]) -> T:
        try:
            result = await self._resilience.call(
                f"object_storage.{operation}",
                invoke,
                retryable=lambda error: not isinstance(error, (FileNotFoundError, ValueError)),
            )
        except Exception:
            self._telemetry.increment(
                "accos_object_storage_operations_total",
                operation=operation,
                outcome="error",
            )
            raise
        self._telemetry.increment(
            "accos_object_storage_operations_total",
            operation=operation,
            outcome="success",
        )
        return result


def _stored_object(object_key: str, value: Object) -> StoredObject:
    metadata = value.metadata or {}
    content_hash = metadata.get("x-amz-meta-sha256", metadata.get("sha256", ""))
    return StoredObject(
        object_key,
        content_hash,
        value.content_type or "application/octet-stream",
        int(value.size or 0),
    )
