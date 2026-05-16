"""
OkChat — Async Database Session
SQLAlchemy 2.0 async session factory with per-request session lifecycle.
Uses a context-local session to avoid passing it through call chains.
"""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from okchat.core.config import DatabaseSettings

# Module-level engine and session factory — created once at startup
_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(settings: DatabaseSettings) -> None:
    """
    Initialize the async engine and session factory.
    Call once during application lifespan startup.
    """
    global _engine, _async_session_factory

    _engine = create_async_engine(
        settings.url.get_secret_value(),
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        pool_timeout=settings.pool_timeout,
        pool_pre_ping=True,  # Validate connections before use
        echo=settings.echo,
    )

    _async_session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Avoid implicit lazy-loading after commit
        autocommit=False,
        autoflush=False,
    )


async def close_db() -> None:
    """Dispose the engine — call during application lifespan shutdown."""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _engine


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for a single database session (use case / service level).
    Commits on success, rolls back on exception.

    Usage in use cases:
        async with get_db_session() as session:
            ...
    """
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session per request.
    The session is committed/rolled back automatically.

    Usage in routers:
        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with get_db_session() as session:
        yield session
