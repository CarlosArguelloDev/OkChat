"""
OkChat — FastAPI Application Factory
Creates and configures the FastAPI app instance.
Uses factory pattern for testability (can create separate instances per test).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from okchat.api.health import health_router
from okchat.api.v1.router import v1_router
from okchat.core.config import get_settings
from okchat.core.errors import register_error_handlers
from okchat.core.middleware.correlation import CorrelationIdMiddleware
from okchat.lifespan import lifespan


def create_app() -> FastAPI:
    """
    Application factory.
    Returns a fully configured FastAPI instance.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="OkChat — Multi-channel Conversational AI API",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Middleware (order matters — outer to inner) ────────────────────────────
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CorrelationIdMiddleware)

    # ── Error Handlers ────────────────────────────────────────────────────────
    register_error_handlers(app)

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(health_router)
    app.include_router(v1_router)

    return app


# Module-level app instance for uvicorn/gunicorn
app = create_app()
