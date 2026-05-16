"""
OkChat — Application Lifespan
Handles startup and shutdown of all shared resources.
FastAPI lifespan replaces the deprecated on_event decorators.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import FastAPI

from okchat.core.config import get_settings
from okchat.core.logging import get_logger, setup_logging
from okchat.infrastructure.database.session import close_db, init_db

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan context manager.
    Everything before `yield` runs on startup.
    Everything after `yield` runs on shutdown.
    """
    settings = get_settings()

    # ── Startup ───────────────────────────────────────────────────────────────
    setup_logging(
        log_level=settings.log_level,
        json_logs=settings.is_production,
    )
    logger.info("app.starting", environment=settings.environment, version=settings.app_version)

    # Initialize database connection pool
    init_db(settings.db)
    logger.info("database.initialized")

    # Initialize Redis
    redis_client = aioredis.from_url(
        settings.redis.url.get_secret_value(),
        decode_responses=True,
        max_connections=settings.redis.pool_size,
    )
    # Verify Redis connection
    await redis_client.ping()
    logger.info("redis.initialized")

    # Store redis client in app state so dependencies can access it
    app.state.redis = redis_client

    logger.info("app.started")

    yield  # ── Application runs here ──────────────────────────────────────────

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("app.shutting_down")

    await redis_client.aclose()
    logger.info("redis.closed")

    await close_db()
    logger.info("database.closed")

    logger.info("app.stopped")
