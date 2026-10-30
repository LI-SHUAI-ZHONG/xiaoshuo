"""Ports owned by the tools module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from uuid import UUID

    from accos.modules.tools.domain import ToolCallRecord, ToolExecution, ToolResult


class ToolExecutor(Protocol):
    """Execute one already authorized and scope-checked tool call."""

    async def execute(self, execution: ToolExecution) -> ToolResult: ...


class ToolCallLedger(Protocol):
    """Append-only tool call audit ledger."""

    async def append(self, record: ToolCallRecord) -> None: ...

    async def for_workflow(
        self, workspace_id: UUID, workflow_run_id: UUID
    ) -> tuple[ToolCallRecord, ...]: ...
