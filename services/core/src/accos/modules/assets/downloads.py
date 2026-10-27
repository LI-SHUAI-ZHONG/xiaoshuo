"""Short-lived signed download claims; signatures never replace current authorization."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
from typing import TYPE_CHECKING
from uuid import UUID

from accos.kernel.errors import ConfigurationError, PermissionDeniedError

if TYPE_CHECKING:
    from accos.kernel.auth_settings import AuthSettings
    from accos.kernel.clock import Clock
    from accos.kernel.security import SecurityContext


class VersionDownloadSigner:
    def __init__(self, config: AuthSettings, clock: Clock) -> None:
        self._config, self._clock = config, clock

    def issue(self, context: SecurityContext, project: UUID, asset: UUID, version: UUID) -> str:
        key_id = self._config.active_key_id
        if key_id not in self._config.secret_keys:
            raise ConfigurationError("Configure the installation keyring to sign download URLs.")
        claims = [
            key_id,
            str(context.actor_id),
            str(context.workspace_id),
            str(project),
            str(asset),
            str(version),
            int(self._clock.now().timestamp()) + 300,
        ]
        payload = (
            base64.urlsafe_b64encode(json.dumps(claims, separators=(",", ":")).encode())
            .decode()
            .rstrip("=")
        )
        return payload + "." + self._signature(key_id, payload)

    def verify(
        self, token: str, context: SecurityContext, project: UUID, asset: UUID, version: UUID
    ) -> None:
        try:
            if len(token) > 2048:
                raise ValueError
            payload, signature = token.split(".")
            claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
            if not isinstance(claims, list) or len(claims) != 7:
                raise ValueError
            if claims[1:6] != [
                str(context.actor_id),
                str(context.workspace_id),
                str(project),
                str(asset),
                str(version),
            ]:
                raise ValueError
            if (
                not isinstance(claims[6], int)
                or not self._clock.now().timestamp()
                < claims[6]
                <= self._clock.now().timestamp() + 300
            ):
                raise ValueError
            if not hmac.compare_digest(self._signature(claims[0], payload), signature):
                raise ValueError
        except (ValueError, TypeError, KeyError, binascii.Error):
            raise PermissionDeniedError() from None

    def _signature(self, key_id: str, payload: str) -> str:
        derived = hmac.digest(
            self._config.secret_keys[key_id].encode(), b"accos-version-download-v1", "sha256"
        )
        return hmac.new(derived, payload.encode(), hashlib.sha256).hexdigest()
