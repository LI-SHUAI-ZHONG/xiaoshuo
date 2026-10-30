"""SQLAlchemy implementation of the application-controlled unit of work."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from sqlalchemy.orm.exc import StaleDataError

from accos.kernel.errors import ConcurrencyConflictError, InvalidStateError

if TYPE_CHECKING:
    from types import TracebackType

    from sqlalchemy.ext.asyncio import AsyncSession

    from accos.adapters.persistence.database import AsyncSessionFactory


class SqlAlchemyUnitOfWork:
    """Own exactly one async session and never commit implicitly."""

    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions
        self._session: AsyncSession | None = None

    @property
    def session(self) -> AsyncSession:
        """Expose the session only to repository adapters assembled around this UoW."""
        if self._session is None:
            raise InvalidStateError("unit of work is not active")
        return self._session

    async def __aenter__(self) -> Self:
        """Open one explicit database transaction."""
        if self._session is not None:
            raise InvalidStateError("unit of work is already active")
        self._session = self._sessions()
        await self._session.begin()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Always roll back unfinished work, then close the session."""
        del exc_type, exc_value, traceback
        session = self.session
        try:
            if session.in_transaction():
                await session.rollback()
        finally:
            await session.close()
            self._session = None

    async def commit(self) -> None:
        """Commit and translate optimistic-lock failures to a stable kernel error."""
        session = self.session
        try:
            await session.commit()
        except StaleDataError:
            await session.rollback()
            raise ConcurrencyConflictError from None

    async def rollback(self) -> None:
        """Discard the current transaction without closing the unit of work."""
        await self.session.rollback()
