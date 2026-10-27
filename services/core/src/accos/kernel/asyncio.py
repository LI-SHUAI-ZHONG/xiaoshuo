"""Cross-platform event-loop factories required by async database drivers."""

from __future__ import annotations

import asyncio


def selector_loop_factory() -> asyncio.AbstractEventLoop:
    """Create the selector loop supported by psycopg on every platform."""
    return asyncio.SelectorEventLoop()
