"""
OkChat — In-Process Event Bus
Lightweight pub/sub for decoupling modules within the monolith.
In Phase 2, replace publish() with a Redis Streams / RabbitMQ adapter
while keeping the same interface.
"""
import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable, Coroutine
from uuid import UUID, uuid4

from okchat.core.logging import get_logger

logger = get_logger(__name__)

# Type alias for async event handler
AsyncHandler = Callable[["DomainEvent"], Coroutine[Any, Any, None]]


@dataclass(frozen=True)
class DomainEvent:
    """
    Base domain event. All events must subclass this.
    Follows CloudEvents naming: {domain}.{entity}.{action}.{version}
    """
    event_id: UUID = field(default_factory=uuid4)
    event_type: str = ""
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    tenant_id: UUID | None = None
    payload: dict[str, Any] = field(default_factory=dict)


class EventBus:
    """
    Async in-process event bus.
    Handlers are called concurrently within an asyncio.gather().
    Failures in one handler do NOT block others.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[AsyncHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: AsyncHandler) -> None:
        """Register a handler for an event type."""
        self._handlers[event_type].append(handler)
        logger.debug("event_bus.subscribed", event_type=event_type, handler=handler.__qualname__)

    def unsubscribe(self, event_type: str, handler: AsyncHandler) -> None:
        """Remove a handler."""
        handlers = self._handlers.get(event_type, [])
        self._handlers[event_type] = [h for h in handlers if h is not handler]

    async def publish(self, event: DomainEvent) -> None:
        """
        Publish an event to all registered handlers.
        Runs all handlers concurrently. Logs but does not re-raise individual failures.
        """
        handlers = self._handlers.get(event.event_type, [])
        if not handlers:
            logger.debug("event_bus.no_handlers", event_type=event.event_type)
            return

        logger.info(
            "event_bus.publishing",
            event_type=event.event_type,
            event_id=str(event.event_id),
            handlers_count=len(handlers),
        )

        results = await asyncio.gather(
            *[handler(event) for handler in handlers],
            return_exceptions=True,
        )

        for result, handler in zip(results, handlers):
            if isinstance(result, Exception):
                logger.error(
                    "event_bus.handler_failed",
                    event_type=event.event_type,
                    handler=handler.__qualname__,
                    error=str(result),
                )


# Singleton event bus — one per process
event_bus = EventBus()
