"""Async SQLAlchemy engine, session factory, lifecycle, and readiness probe."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from accos.kernel.health import CheckStatus, HealthCheck
from accos.kernel.logging import get_logger, log_event

if TYPE_CHECKING:
    from accos.kernel.settings import OptionalSettings

AsyncSessionFactory = async_sessionmaker[AsyncSession]


@dataclass(frozen=True, slots=True)
class EngineOptions:
    """Validated connection-pool settings supplied by the composition root."""

    pool_size: int
    max_overflow: int
    pool_timeout_seconds: float
    pool_recycle_seconds: int

    @classmethod
    def from_settings(cls, settings: OptionalSettings) -> EngineOptions:
        """Map framework-neutral runtime settings to adapter options."""
        return cls(
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout_seconds=settings.db_pool_timeout_seconds,
            pool_recycle_seconds=settings.db_pool_recycle_seconds,
        )


def build_async_engine(database_url: str, options: EngineOptions) -> AsyncEngine:
    """Create the main application database pool; schema creation is never implicit."""
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=options.pool_size,
        max_overflow=options.max_overflow,
        pool_timeout=options.pool_timeout_seconds,
        pool_recycle=options.pool_recycle_seconds,
    )


def build_unpooled_async_engine(database_url: str) -> AsyncEngine:
    """Create a cross-event-loop-safe engine for the Celery consumer boundary."""
    return create_async_engine(database_url, pool_pre_ping=True, poolclass=NullPool)


@dataclass(slots=True)
class DatabaseRuntime:
    """Long-lived database resources owned by one runtime boundary."""

    engine: AsyncEngine
    sessions: AsyncSessionFactory
    name: str = "persistence"
    logger: logging.Logger = field(default_factory=lambda: get_logger("lifecycle"), repr=False)

    @classmethod
    def create(cls, database_url: str, options: EngineOptions) -> DatabaseRuntime:
        """Build an engine and non-expiring async session factory."""
        engine = build_async_engine(database_url, options)
        return cls(
            engine=engine,
            sessions=async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession),
        )

    @classmethod
    def create_unpooled(
        cls,
        database_url: str,
        *,
        name: str = "unpooled-persistence",
    ) -> DatabaseRuntime:
        """Build a NullPool session factory safe to invoke from successive event loops."""
        engine = build_unpooled_async_engine(database_url)
        return cls(
            engine=engine,
            sessions=async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession),
            name=name,
        )

    async def startup(self) -> None:
        """Keep acquisition lazy so readiness owns external dependency checks."""
        log_event(self.logger, logging.INFO, "module_started", module=self.name)

    async def shutdown(self) -> None:
        """Close every pooled database connection."""
        await self.engine.dispose()
        log_event(self.logger, logging.INFO, "module_stopped", module=self.name)


@dataclass(frozen=True, slots=True)
class DatabaseHealthProbe:
    """Run readiness through the shared asynchronous engine pool."""

    engine: AsyncEngine
    name: str = "postgresql"
    critical: bool = True

    async def check(self) -> HealthCheck:
        """Verify the database accepts a trivial statement."""
        async with self.engine.connect() as connection:
            value = (await connection.execute(text("SELECT 1"))).scalar_one()
        if value != 1:
            raise RuntimeError("PostgreSQL health query returned an invalid result")
        return HealthCheck(self.name, CheckStatus.HEALTHY, self.critical, "query_ok")
