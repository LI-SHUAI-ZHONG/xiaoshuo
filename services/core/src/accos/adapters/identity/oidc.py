"""OIDC authorization code / S256 PKCE, pinned HTTPS endpoints and RS256 JWKS rotation."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import math
import secrets
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast
from urllib.error import URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15

from accos.kernel.errors import AuthenticationRequiredError, ConfigurationError

if TYPE_CHECKING:
    from accos.kernel.auth_settings import AuthSettings


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        return None


def _decode64(value: str) -> bytes:
    return base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)


def _json_unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field")
        result[key] = value
    return result


def _fetch_json(url: str, form: dict[str, str] | None = None) -> dict[str, Any]:
    if not url.startswith("https://"):
        raise ConfigurationError("OIDC endpoints must use HTTPS.")
    data = None if form is None else urlencode(form).encode()
    request = Request(
        url,
        data=data,
        headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        # No ambient proxy credentials and no redirects to another host.
        with build_opener(ProxyHandler({}), _NoRedirect()).open(request, timeout=8) as response:
            raw = response.read(1_048_577)
        if len(raw) > 1_048_576:
            raise ValueError("Oversize response")
        document = json.loads(raw, object_pairs_hook=_json_unique)
        if not isinstance(document, dict):
            raise ValueError("Invalid response")
        return cast("dict[str, Any]", document)
    except (URLError, OSError, ValueError):
        raise AuthenticationRequiredError from None


class HttpOidcClient:
    def __init__(self, config: AuthSettings) -> None:
        self._config = config
        self._keys: list[dict[str, Any]] = []
        self._refresh_at = 0.0
        self._lock = asyncio.Lock()

    @property
    def callback_uri(self) -> str:
        return self._config.public_origin + "/api/v1/auth/oidc/callback"

    def authorization_url(self, state: str, nonce: str, verifier: str) -> str:
        if not self._config.oidc_configured:
            raise ConfigurationError("OIDC configuration is incomplete.")
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        params = urlencode(
            {
                "client_id": self._config.oidc_client_id,
                "response_type": "code",
                "scope": "openid",
                "redirect_uri": self.callback_uri,
                "state": state,
                "nonce": nonce,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "response_mode": "query",
            }
        )
        endpoint = urlsplit(self._config.oidc_authorization_endpoint)
        # Preserve provider routing parameters while preventing duplicate security parameters.
        reserved = {key for key, _ in parse_qsl(params)}
        configured = [
            (key, value)
            for key, value in parse_qsl(endpoint.query, keep_blank_values=True)
            if key not in reserved
        ]
        query = urlencode(configured)
        return urlunsplit(endpoint._replace(query=(query + "&" if query else "") + params))

    async def exchange(
        self, code: str, verifier: str, nonce: str, now: datetime
    ) -> tuple[str, str]:
        form = {
            "grant_type": "authorization_code",
            "client_id": self._config.oidc_client_id,
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": self.callback_uri,
        }
        if self._config.oidc_client_secret:
            form["client_secret"] = self._config.oidc_client_secret
        response = await asyncio.to_thread(_fetch_json, self._config.oidc_token_endpoint, form)
        token = response.get("id_token")
        if not isinstance(token, str) or len(token) > 32768:
            raise AuthenticationRequiredError
        return await self.verify_id_token(token, nonce, now)

    async def _refresh(self) -> None:
        async with self._lock:
            document = await asyncio.to_thread(_fetch_json, self._config.oidc_jwks_uri)
            keys = document.get("keys")
            if (
                not isinstance(keys, list)
                or not 1 <= len(keys) <= 100
                or not all(isinstance(k, dict) for k in keys)
            ):
                raise AuthenticationRequiredError
            self._keys, self._refresh_at = keys, time.monotonic() + 300

    async def verify_id_token(self, token: str, nonce: str, now: datetime) -> tuple[str, str]:
        try:
            head, payload, signature = token.split(".")
            header = json.loads(_decode64(head), object_pairs_hook=_json_unique)
            claims = json.loads(_decode64(payload), object_pairs_hook=_json_unique)
            if (
                not isinstance(header, dict)
                or not isinstance(claims, dict)
                or header.get("alg") != "RS256"
                or header.get("crit")
            ):
                raise ValueError("Unsupported token")
            kid = header["kid"]
            if not isinstance(kid, str) or not kid:
                raise ValueError("Missing signing key")
            if time.monotonic() >= self._refresh_at:
                await self._refresh()
            for attempt in range(2):
                matches = [
                    k
                    for k in self._keys
                    if k.get("kid") == kid
                    and k.get("kty") == "RSA"
                    and k.get("use", "sig") == "sig"
                    and k.get("alg", "RS256") == "RS256"
                    and "verify" in k.get("key_ops", ["verify"])
                ]
                try:
                    if len(matches) != 1:
                        raise ValueError("Unknown signing key")
                    key = RSA.construct(
                        (
                            int.from_bytes(_decode64(matches[0]["n"]), "big"),
                            int.from_bytes(_decode64(matches[0]["e"]), "big"),
                        )
                    )
                    if not 2048 <= key.size_in_bits() <= 8192:
                        raise ValueError("Invalid signing key size")
                    pkcs1_15.new(key).verify(
                        SHA256.new(f"{head}.{payload}".encode()), _decode64(signature)
                    )
                    break
                except (ValueError, TypeError, KeyError):
                    if attempt:
                        raise
                    await self._refresh()
            timestamp = now.timestamp()
            for required in ("exp", "iat"):
                value = claims[required]
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise ValueError("Invalid timestamp")
            if claims["exp"] <= timestamp or claims["iat"] > timestamp + 60:
                raise ValueError("Expired or future token")
            if "nbf" in claims and (
                type(claims["nbf"]) not in (int, float)
                or not math.isfinite(claims["nbf"])
                or claims["nbf"] > timestamp + 60
            ):
                raise ValueError("Token not yet valid")
            audience = claims["aud"]
            audiences = [audience] if isinstance(audience, str) else audience
            if (
                not isinstance(audiences, list)
                or not all(isinstance(a, str) for a in audiences)
                or self._config.oidc_client_id not in audiences
            ):
                raise ValueError("Wrong audience")
            if (len(audiences) > 1 or "azp" in claims) and claims.get(
                "azp"
            ) != self._config.oidc_client_id:
                raise ValueError("Wrong authorized party")
            if (
                claims["iss"] != self._config.oidc_issuer
                or not isinstance(claims.get("nonce"), str)
                or not secrets.compare_digest(claims["nonce"], nonce)
            ):
                raise ValueError("Wrong issuer or nonce")
            subject = claims["sub"]
            if not isinstance(subject, str) or not 1 <= len(subject) <= 500:
                raise ValueError("Missing subject")
            return self._config.oidc_issuer, subject
        except (ValueError, KeyError, TypeError, UnicodeError):
            raise AuthenticationRequiredError from None
