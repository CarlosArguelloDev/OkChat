"""
OkChat — Base Domain Exceptions
Hierarchy allows catching at any level of granularity.
Infrastructure translates these into HTTP errors in error handlers.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OkChatError(Exception):
    """Base for all domain errors. Never raise Exception directly."""
    message: str
    code: str = "INTERNAL_ERROR"
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


@dataclass
class NotFoundError(OkChatError):
    """Entity not found."""
    code: str = "NOT_FOUND"


@dataclass
class UnauthorizedError(OkChatError):
    """Authentication required."""
    code: str = "UNAUTHORIZED"


@dataclass
class ForbiddenError(OkChatError):
    """Authenticated but not authorized."""
    code: str = "FORBIDDEN"


@dataclass
class ConflictError(OkChatError):
    """Duplicate or conflicting resource."""
    code: str = "CONFLICT"


@dataclass
class ValidationError(OkChatError):
    """Domain validation failure (not HTTP validation)."""
    code: str = "VALIDATION_ERROR"


@dataclass
class ExternalServiceError(OkChatError):
    """Upstream provider (OpenAI, Deepgram, etc.) failed."""
    code: str = "EXTERNAL_SERVICE_ERROR"
    provider: str = ""


@dataclass
class RateLimitError(OkChatError):
    """Rate limit exceeded at domain level."""
    code: str = "RATE_LIMIT_EXCEEDED"
    retry_after_seconds: int = 60
