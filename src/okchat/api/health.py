"""
OkChat — Health Check Router
Provides Kubernetes liveness and readiness probes.
Readiness checks DB + Redis connectivity.
"""
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text

from okchat.infrastructure.database.session import get_engine

health_router = APIRouter(tags=["Health"])


@health_router.get(
    "/health/live",
    summary="Liveness probe — is the process alive?",
    status_code=status.HTTP_200_OK,
)
async def liveness() -> dict:
    """
    Returns 200 if the process is running.
    Kubernetes uses this to decide whether to restart the pod.
    Should NEVER check external dependencies here.
    """
    return {"status": "alive"}


@health_router.get(
    "/health/ready",
    summary="Readiness probe — can the pod serve traffic?",
)
async def readiness(request: Request) -> JSONResponse:
    """
    Returns 200 if DB and Redis are reachable.
    Kubernetes uses this to decide whether to route traffic.
    """
    checks: dict[str, str] = {}
    healthy = True

    # Check database
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        healthy = False

    # Check Redis
    try:
        redis: Redis = request.app.state.redis
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        healthy = False

    return JSONResponse(
        status_code=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "ready" if healthy else "not_ready", "checks": checks},
    )
