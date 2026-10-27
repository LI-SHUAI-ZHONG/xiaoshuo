"""Runtime module registration and lifecycle coordination."""

from __future__ import annotations

from typing import Protocol

from accos.kernel.errors import InvalidStateError


class RuntimeModule(Protocol):
    """Lifecycle contract implemented by registered runtime modules."""

    name: str

    async def startup(self) -> None:
        """Acquire module resources."""
        ...

    async def shutdown(self) -> None:
        """Release module resources."""
        ...


class ModuleRegistry:
    """Start modules in registration order and stop them in reverse order."""

    def __init__(self, modules: tuple[RuntimeModule, ...]) -> None:
        names = tuple(module.name for module in modules)
        if len(names) != len(set(names)):
            raise ValueError("runtime module names must be unique")
        self._modules = modules
        self._started: list[RuntimeModule] = []

    @property
    def names(self) -> tuple[str, ...]:
        """Return registered module names in startup order."""
        return tuple(module.name for module in self._modules)

    async def startup(self) -> None:
        """Start every module, rolling back a partial startup."""
        if self._started:
            raise InvalidStateError("runtime modules are already started")
        try:
            for module in self._modules:
                await module.startup()
                self._started.append(module)
        except Exception:
            await self._stop_started()
            raise

    async def shutdown(self) -> None:
        """Stop all modules that started successfully."""
        await self._stop_started()

    async def _stop_started(self) -> None:
        while self._started:
            await self._started.pop().shutdown()
