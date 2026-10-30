"""Bounded keyset cursors bind immutable sort keys to the requested collection."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from datetime import datetime
from uuid import UUID

from accos.kernel.errors import InvalidRequestError


def encode_keyset(created_at: datetime, identifier: UUID, scope: str) -> str:
    value = json.dumps(
        [created_at.isoformat(), str(identifier), hashlib.sha256(scope.encode()).hexdigest()]
    )
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def decode_keyset(cursor: str, scope: str) -> tuple[datetime, UUID]:
    try:
        if len(cursor) > 2048:
            raise ValueError
        value = json.loads(
            base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True)
        )
        if (
            not isinstance(value, list)
            or len(value) != 3
            or value[2] != hashlib.sha256(scope.encode()).hexdigest()
        ):
            raise ValueError
        moment, identifier = datetime.fromisoformat(value[0]), UUID(value[1])
        if moment.tzinfo is None:
            raise ValueError
        return moment, identifier
    except (ValueError, TypeError, binascii.Error):
        raise InvalidRequestError("The cursor does not belong to this collection.") from None
