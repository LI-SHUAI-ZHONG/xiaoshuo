"""Argon2id passwords and AES-256-GCM credentials using installed audited primitives."""

from __future__ import annotations

import base64
import hashlib
import os
import re
import secrets
from typing import Mapping

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from Crypto.Cipher import AES

from accos.kernel.errors import ConfigurationError, InvalidRequestError

_PASSWORDS = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)


def token_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def password_hash(value: str) -> str:
    if not 12 <= len(value) <= 256:
        raise InvalidRequestError("Passwords must contain 12 to 256 characters.")
    return _PASSWORDS.hash(value)


def password_matches(encoded: str, value: str) -> bool:
    if len(value) > 256:
        return False
    try:
        return _PASSWORDS.verify(encoded, value)
    except (VerificationError, InvalidHashError):
        return False


class CredentialCipher:
    def __init__(self, keys: Mapping[str, str], active: str) -> None:
        self._keys = keys
        self.active = active

    @property
    def configured(self) -> bool:
        try:
            self._key(self.active)
        except ConfigurationError:
            return False
        return True

    def _key(self, key_id: str) -> bytes:
        try:
            key = base64.b64decode(self._keys[key_id], validate=True)
        except (KeyError, ValueError):
            raise ConfigurationError("Credential master key is missing or invalid.") from None
        if len(key) != 32:
            raise ConfigurationError("Credential master keys must contain 32 random bytes.")
        return key

    def encrypt(self, value: str, binding: str) -> str:
        cipher = AES.new(self._key(self.active), AES.MODE_GCM, nonce=secrets.token_bytes(12))
        cipher.update(binding.encode())
        ciphertext, tag = cipher.encrypt_and_digest(value.encode())
        return base64.b64encode(bytes(cipher.nonce) + tag + ciphertext).decode()

    def decrypt(self, value: str, key_id: str, binding: str) -> str:
        key = self._key(key_id)
        try:
            raw = base64.b64decode(value, validate=True)
            cipher = AES.new(key, AES.MODE_GCM, nonce=raw[:12])
            cipher.update(binding.encode())
            return cipher.decrypt_and_verify(raw[28:], raw[12:28]).decode()
        except (ValueError, UnicodeError):
            raise ConfigurationError(
                "Credential cannot be decrypted with the configured keyring."
            ) from None


def external_secret(reference: str) -> str:
    if re.fullmatch(r"env://ACCOS_PROVIDER_SECRET_[A-Z0-9_]{1,80}", reference) is None:
        raise InvalidRequestError(
            "External credentials must name an ACCOS_PROVIDER_SECRET_ environment entry."
        )
    value = os.environ.get(reference.removeprefix("env://"))
    if not value:
        raise ConfigurationError("The external credential is not configured.")
    return value
