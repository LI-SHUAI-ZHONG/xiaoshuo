"""Asset-to-knowledge source adapter using only asset public contracts."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from accos.modules.assets.public import AssetStatus, ProcessingStatus
from accos.modules.knowledge.public import (
    IngestionStatus,
    KnowledgeErrorCode,
    KnowledgePipelineError,
    SourceSnapshot,
)

if TYPE_CHECKING:
    from uuid import UUID

    from accos.modules.assets.public import AssetRepository, ObjectStorage


class AssetSourceReader:
    """Resolve the current immutable asset version and verify bytes on every read."""

    def __init__(self, assets: AssetRepository, storage: ObjectStorage) -> None:
        self._assets = assets
        self._storage = storage

    async def resolve(self, workspace_id: UUID, project_id: UUID, asset_id: UUID) -> SourceSnapshot:
        pair = await self._assets.get(workspace_id, project_id, asset_id)
        if pair is None:
            raise KnowledgePipelineError(
                KnowledgeErrorCode.SOURCE_UNAVAILABLE,
                IngestionStatus.EXTRACTING,
                retryable=False,
            )
        asset, version = pair
        if (
            asset.status is not AssetStatus.ACTIVE
            or version.processing_status is not ProcessingStatus.AVAILABLE
        ):
            raise KnowledgePipelineError(
                KnowledgeErrorCode.SOURCE_UNAVAILABLE,
                IngestionStatus.EXTRACTING,
                retryable=True,
            )
        return SourceSnapshot(
            workspace_id,
            project_id,
            asset.id,
            version.id,
            version.version_number,
            version.object_key,
            version.content_hash,
            version.media_type,
        )

    async def read(self, source: SourceSnapshot) -> bytes:
        try:
            data = await self._storage.get(source.object_key)
        except Exception as error:
            raise KnowledgePipelineError(
                KnowledgeErrorCode.SOURCE_UNAVAILABLE,
                IngestionStatus.EXTRACTING,
                retryable=True,
            ) from error
        if hashlib.sha256(data).hexdigest() != source.content_hash:
            raise KnowledgePipelineError(
                KnowledgeErrorCode.SOURCE_INTEGRITY_FAILED,
                IngestionStatus.EXTRACTING,
                retryable=False,
            )
        return data


class NotConfiguredExternalSourceReader:
    """Fail-closed placeholder for external database and remote source adapters."""

    async def resolve(self, workspace_id: UUID, project_id: UUID, asset_id: UUID) -> SourceSnapshot:
        del workspace_id, project_id, asset_id
        raise KnowledgePipelineError(
            KnowledgeErrorCode.SOURCE_NOT_CONFIGURED,
            IngestionStatus.EXTRACTING,
            retryable=False,
        )

    async def read(self, source: SourceSnapshot) -> bytes:
        del source
        raise KnowledgePipelineError(
            KnowledgeErrorCode.SOURCE_NOT_CONFIGURED,
            IngestionStatus.EXTRACTING,
            retryable=False,
        )
