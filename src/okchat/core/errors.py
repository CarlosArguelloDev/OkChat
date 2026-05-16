"""
OkChat — Global HTTP Error Handlers
Translates domain exceptions and Pydantic validation errors
into consistent JSON error responses.
"""
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from okchat.core.exceptions import (
    ConflictError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    OkChatError,
    RateLimitError,
    UnauthorizedError,
    ValidationError,
)

DOMAIN_ERROR_STATUS_MAP: dict[type[OkChatError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    UnauthorizedError: status.HTTP_401_UNAUTHORIZED,
    ForbiddenError: status.HTTP_403_FORBIDDEN,
    ConflictError: status.HTTP_409_CONFLICT,
    ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ExternalServiceError: status.HTTP_502_BAD_GATEWAY,
    RateLimitError: status.HTTP_429_TOO_MANY_REQUESTS,
    OkChatError: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def _error_body(code: str, message: str, details: dict | None = None) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        }
    }


def register_error_handlers(app: FastAPI) -> None:
    """Register all error handlers on the FastAPI app."""

    @app.exception_handler(RequestValidationError)
    async def pydantic_validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                details={"errors": exc.errors()},
            ),
        )

    @app.exception_handler(OkChatError)
    async def domain_error_handler(
        request: Request, exc: OkChatError
    ) -> JSONResponse:
        http_status = DOMAIN_ERROR_STATUS_MAP.get(
            type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        headers: dict[str, str] = {}
        if isinstance(exc, RateLimitError):
            headers["Retry-After"] = str(exc.retry_after_seconds)

        return JSONResponse(
            status_code=http_status,
            content=_error_body(exc.code, exc.message, exc.details),
            headers=headers,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred",
            ),
        )
