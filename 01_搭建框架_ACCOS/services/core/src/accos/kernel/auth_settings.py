"""Host-controlled authentication configuration; never writable through workspace settings."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Mapping
from urllib.parse import urlsplit
from uuid import UUID

from accos.kernel.errors import ConfigurationError

AUTH_DEFAULTS = {
    "ACCOS_IDENTITY_CONFIG_FILE": "",
    "ACCOS_PUBLIC_ORIGIN": "http://localhost:3000",
    "ACCOS_ALLOWED_HOSTS": "localhost,127.0.0.1,[::1]",
    "ACCOS_BOOTSTRAP_TOKEN_SHA256": "",
    "ACCOS_BOOTSTRAP_ADOPT_WORKSPACE_ID": "",
    "ACCOS_SESSION_HOURS": "12",
    "ACCOS_SECRET_KEYS_JSON": "{}",
    "ACCOS_SECRET_ACTIVE_KEY_ID": "",
    "ACCOS_OIDC_ISSUER": "",
    "ACCOS_OIDC_CLIENT_ID": "",
    "ACCOS_OIDC_CLIENT_SECRET": "",
    "ACCOS_OIDC_AUTHORIZATION_ENDPOINT": "",
    "ACCOS_OIDC_TOKEN_ENDPOINT": "",
    "ACCOS_OIDC_JWKS_URI": "",
}


@dataclass(frozen=True, slots=True)
class AuthSettings:
    public_origin: str = "http://localhost:3000"
    allowed_hosts: tuple[str, ...] = ("localhost", "127.0.0.1", "[::1]")
    bootstrap_digest: str = field(default="", repr=False)
    adopt_workspace_id: UUID | None = None
    session_hours: int = 12
    secret_keys: Mapping[str, str] = field(default_factory=dict, repr=False)
    active_key_id: str = ""
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = field(default="", repr=False)
    oidc_authorization_endpoint: str = ""
    oidc_token_endpoint: str = ""
    oidc_jwks_uri: str = ""

    @property
    def secure_cookie(self) -> bool:
        return self.public_origin.startswith("https://")

    @property
    def oidc_configured(self) -> bool:
        return all(
            (
                self.oidc_issuer,
                self.oidc_client_id,
                self.oidc_authorization_endpoint,
                self.oidc_token_endpoint,
                self.oidc_jwks_uri,
            )
        )

    @classmethod
    def from_values(cls, values: Mapping[str, str]) -> AuthSettings:
        origin = values["ACCOS_PUBLIC_ORIGIN"].rstrip("/")
        parsed = urlsplit(origin)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.path
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or (
                parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
            )
        ):
            raise ConfigurationError(
                "Public origin must use HTTPS, except explicit loopback development."
            )
        try:
            keys = json.loads(values["ACCOS_SECRET_KEYS_JSON"])
            hours = int(values["ACCOS_SESSION_HOURS"])
            adopt = (
                UUID(values["ACCOS_BOOTSTRAP_ADOPT_WORKSPACE_ID"])
                if values["ACCOS_BOOTSTRAP_ADOPT_WORKSPACE_ID"]
                else None
            )
        except (ValueError, TypeError):
            raise ConfigurationError("Authentication configuration is invalid.") from None
        if (
            not isinstance(keys, dict)
            or not all(isinstance(k, str) and isinstance(v, str) for k, v in keys.items())
            or not 1 <= hours <= 168
        ):
            raise ConfigurationError("Authentication keyring or session duration is invalid.")
        oidc_names = ("ISSUER", "AUTHORIZATION_ENDPOINT", "TOKEN_ENDPOINT", "JWKS_URI")
        for name in oidc_names:
            value = values[f"ACCOS_OIDC_{name}"]
            url = urlsplit(value)
            if value and (
                url.scheme != "https"
                or not url.hostname
                or url.username
                or url.password
                or url.fragment
            ):
                raise ConfigurationError(
                    "OIDC endpoints must use HTTPS without embedded credentials."
                )
        return cls(
            public_origin=origin,
            allowed_hosts=tuple(
                x.strip().lower() for x in values["ACCOS_ALLOWED_HOSTS"].split(",") if x.strip()
            ),
            bootstrap_digest=values["ACCOS_BOOTSTRAP_TOKEN_SHA256"],
            session_hours=hours,
            adopt_workspace_id=adopt,
            secret_keys=keys,
            active_key_id=values["ACCOS_SECRET_ACTIVE_KEY_ID"],
            oidc_issuer=values["ACCOS_OIDC_ISSUER"],
            oidc_client_id=values["ACCOS_OIDC_CLIENT_ID"],
            oidc_client_secret=values["ACCOS_OIDC_CLIENT_SECRET"],
            oidc_authorization_endpoint=values["ACCOS_OIDC_AUTHORIZATION_ENDPOINT"],
            oidc_token_endpoint=values["ACCOS_OIDC_TOKEN_ENDPOINT"],
            oidc_jwks_uri=values["ACCOS_OIDC_JWKS_URI"],
        )
