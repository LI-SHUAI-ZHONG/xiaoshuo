"""Run a bounded execution-07 object-store write/read/hash probe."""

from __future__ import annotations

import asyncio
import hashlib
import sys
from urllib.parse import urlsplit
from uuid import uuid4

from minio import Minio

from accos.adapters.assets import MinioObjectStorage
from accos.kernel.settings import load_settings
from accos.modules.assets.public import object_key_for


async def verify() -> None:
    """Write and verify one technical object, then remove only that probe object."""
    settings = load_settings()
    required, optional = settings.required, settings.optional
    storage = MinioObjectStorage(
        endpoint=required.s3_endpoint,
        bucket=required.s3_bucket,
        access_key=required.s3_access_key,
        secret_key=required.s3_secret_key,
        secure=optional.s3_use_ssl,
        region=optional.s3_region,
    )
    cleanup = Minio(
        urlsplit(required.s3_endpoint).netloc,
        access_key=required.s3_access_key,
        secret_key=required.s3_secret_key,
        secure=optional.s3_use_ssl,
        region=optional.s3_region,
    )
    key = object_key_for(uuid4(), uuid4(), uuid4(), uuid4())
    data = b"fixture-object"
    digest = hashlib.sha256(data).hexdigest()
    try:
        written = await storage.put(
            key,
            data,
            media_type="application/octet-stream",
            content_hash=digest,
        )
        if await storage.get(key) != data or await storage.stat(key) != written:
            raise RuntimeError("stage07 object storage verification failed")
    finally:
        await asyncio.to_thread(cleanup.remove_object, required.s3_bucket, key)
    sys.stdout.write("stage07 object storage: PASS\n")


if __name__ == "__main__":
    asyncio.run(verify(), loop_factory=asyncio.SelectorEventLoop)
