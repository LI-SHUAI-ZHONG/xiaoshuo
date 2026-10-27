"""Small, stable cross-cutting API contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass

API_VERSION = "v1"
DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 100
MAX_IDEMPOTENCY_KEY_LENGTH = 128
_SEMANTIC_VERSION = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


@dataclass(frozen=True, slots=True)
class VersionNumber:
    """Strict semantic version text used at process boundaries."""

    value: str

    def __post_init__(self) -> None:
        if _SEMANTIC_VERSION.fullmatch(self.value) is None:
            raise ValueError("version must use major.minor.patch format")


@dataclass(frozen=True, slots=True)
class PageRequest:
    """Offset pagination limits shared by future resource APIs."""

    offset: int = 0
    limit: int = DEFAULT_PAGE_LIMIT

    def __post_init__(self) -> None:
        if self.offset < 0:
            raise ValueError("offset must be non-negative")
        if not 1 <= self.limit <= MAX_PAGE_LIMIT:
            raise ValueError(f"limit must be between 1 and {MAX_PAGE_LIMIT}")


@dataclass(frozen=True, slots=True)
class IdempotencyKey:
    """Validated opaque idempotency key."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or self.value.strip() != self.value:
            raise ValueError("idempotency key must be non-empty and trimmed")
        if len(self.value) > MAX_IDEMPOTENCY_KEY_LENGTH or not self.value.isascii():
            raise ValueError("idempotency key must be at most 128 ASCII characters")
