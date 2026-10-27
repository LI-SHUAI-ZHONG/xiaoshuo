"""Development and decoder-neutral OIDC/JWT identity-provider adapters."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from accos.kernel.errors import AuthenticationRequiredError
from accos.kernel.security import ActorKind
from accos.modules.identity.domain import AuthenticatedIdentity


class JwtDecoder(Protocol):
    """Cryptographic JWT decoder boundary supplied by a deployment adapter."""

    def decode(self, token: str) -> dict[str, object]:
        """Verify signature and return claims, or raise TokenVerificationError."""
        ...


class TokenVerificationError(Exception):
    """Internal decoder failure never exposed to callers."""


@dataclass(frozen=True, slots=True)
class OidcJwtIdentityProvider:
    """Validate issuer, audience, expiry, subject, and principal kind after decoding."""

    decoder: JwtDecoder
    issuer: str
    audience: str

    async def authenticate(self, credential: str, *, now: datetime) -> AuthenticatedIdentity:
        try:
            claims = self.decoder.decode(credential)
        except TokenVerificationError:
            raise AuthenticationRequiredError from None
        subject = claims.get("sub")
        issuer = claims.get("iss")
        expiry = claims.get("exp")
        audience = claims.get("aud")
        accepted_audience = (
            self.audience in audience
            if isinstance(audience, list) and all(isinstance(item, str) for item in audience)
            else audience == self.audience
        )
        if (
            not isinstance(subject, str)
            or not subject
            or issuer != self.issuer
            or not accepted_audience
            or not isinstance(expiry, (int, float))
            or expiry <= now.astimezone(UTC).timestamp()
        ):
            raise AuthenticationRequiredError
        actor_kind = (
            ActorKind.SERVICE if claims.get("actor_kind") == ActorKind.SERVICE else ActorKind.USER
        )
        raw_service_id = claims.get("service_identity_id")
        try:
            service_id = UUID(raw_service_id) if isinstance(raw_service_id, str) else None
        except ValueError:
            raise AuthenticationRequiredError from None
        if actor_kind is ActorKind.SERVICE and service_id is None:
            raise AuthenticationRequiredError
        return AuthenticatedIdentity(
            issuer=issuer,
            subject=subject,
            actor_kind=actor_kind,
            service_identity_id=service_id,
        )


@dataclass(frozen=True, slots=True)
class DevelopmentIdentityProvider:
    """Explicit static local credential adapter; never selected in production."""

    credential: str
    approver_credential: str | None = None
    subject: str = "local-development"
    approver_subject: str = "local-development-approver"
    issuer: str = "urn:accos:development"

    async def authenticate(self, credential: str, *, now: datetime) -> AuthenticatedIdentity:
        del now
        if secrets.compare_digest(credential, self.credential):
            return AuthenticatedIdentity(self.issuer, self.subject, ActorKind.USER)
        if self.approver_credential is not None and secrets.compare_digest(
            credential, self.approver_credential
        ):
            return AuthenticatedIdentity(self.issuer, self.approver_subject, ActorKind.USER)
        raise AuthenticationRequiredError


@dataclass(frozen=True, slots=True)
class RejectingIdentityProvider:
    """Secure runtime default until a production OIDC decoder is explicitly injected."""

    async def authenticate(self, credential: str, *, now: datetime) -> AuthenticatedIdentity:
        del credential, now
        raise AuthenticationRequiredError
