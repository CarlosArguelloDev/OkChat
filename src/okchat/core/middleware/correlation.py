"""
OkChat — Correlation ID Middleware
Injects X-Request-ID into every request and propagates it to:
 - structlog context vars (available in all log entries)
 - response headers
"""
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

CORRELATION_ID_HEADER = "X-Request-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Reads or generates a correlation ID for every request.
    Binds it to the structlog context so all log lines in this
    request include the same request_id automatically.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        correlation_id = request.headers.get(
            CORRELATION_ID_HEADER, str(uuid.uuid4())
        )

        # Bind to structlog context — available for the entire request lifecycle
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=correlation_id,
            method=request.method,
            path=str(request.url.path),
        )

        response = await call_next(request)
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response
