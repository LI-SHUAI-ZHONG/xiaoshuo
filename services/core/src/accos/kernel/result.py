"""Explicit success and failure result variants."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Success[T]:
    """Successful operation result."""

    value: T


@dataclass(frozen=True, slots=True)
class Failure[E]:
    """Failed operation result."""

    error: E


type Result[T, E] = Success[T] | Failure[E]
