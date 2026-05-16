"""
OkChat — SendMessage Use Case
Application layer orchestrates:
 1. Validate user has access to the conversation
 2. Add user message to conversation aggregate
 3. Get LLM response via injected LLM port
 4. Add assistant message
 5. Save via repository
 6. Publish domain event

No HTTP, no SQLAlchemy, no OpenAI SDK — only ports (Protocols).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import AsyncIterator, Protocol

from okchat.core.exceptions import ForbiddenError, NotFoundError
from okchat.core.logging import get_logger
from okchat.infrastructure.events.bus import DomainEvent, EventBus
from okchat.modules.conversations.domain.entities import (
    Conversation,
    MessageRole,
)
from okchat.modules.conversations.domain.repository import ConversationRepository

logger = get_logger(__name__)


# ── LLM Port (Protocol) — no OpenAI SDK dependency in use case ────────────────


class LLMMessage(Protocol):
    role: str
    content: str


@dataclass
class LLMRequest:
    messages: list[dict[str, str]]
    model: str
    temperature: float = 0.7
    max_tokens: int = 2048


class LLMPort(Protocol):
    """The use case depends on this. OpenAIAdapter, AnthropicAdapter implement it."""

    async def complete(self, request: LLMRequest) -> str:
        """Return full completion as a string."""
        ...

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """Stream completion tokens as they arrive."""
        ...


# ── Input / Output DTOs ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SendMessageInput:
    conversation_id: uuid.UUID
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    text: str
    stream: bool = False


@dataclass(frozen=True)
class SendMessageOutput:
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    assistant_text: str
    tokens_used: int | None


# ── Domain Events ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MessageCreatedEvent(DomainEvent):
    event_type: str = "conversations.message.created.v1"


# ── Use Case ──────────────────────────────────────────────────────────────────


class SendMessageUseCase:
    """
    Orchestrates sending a user message and getting an LLM response.

    Dependencies are injected via constructor — never resolved internally.
    This makes the use case trivially unit-testable with mocks.
    """

    def __init__(
        self,
        repository: ConversationRepository,
        llm: LLMPort,
        event_bus: EventBus,
        default_model: str = "gpt-4o",
    ) -> None:
        self._repo = repository
        self._llm = llm
        self._event_bus = event_bus
        self._default_model = default_model

    async def execute(self, input_dto: SendMessageInput) -> SendMessageOutput:
        # 1. Load conversation
        conversation = await self._repo.get_by_id(input_dto.conversation_id)
        if conversation is None:
            raise NotFoundError(
                message="Conversation not found",
                details={"conversation_id": str(input_dto.conversation_id)},
            )

        # 2. Authorization check (tenant isolation)
        if conversation.tenant_id != input_dto.tenant_id:
            raise ForbiddenError(message="Access denied to this conversation")

        # 3. Add user message via domain aggregate (enforces business rules)
        conversation.add_message(role=MessageRole.USER, text=input_dto.text)

        # 4. Build LLM context from conversation history
        llm_request = self._build_llm_request(conversation)

        # 5. Call LLM through the port
        logger.info(
            "llm.requesting",
            conversation_id=str(input_dto.conversation_id),
            model=llm_request.model,
        )
        assistant_text = await self._llm.complete(llm_request)

        # 6. Add assistant response to aggregate
        assistant_message = conversation.add_message(
            role=MessageRole.ASSISTANT,
            text=assistant_text,
        )

        # 7. Persist the updated aggregate
        await self._repo.save(conversation)

        # 8. Publish domain event (fire and forget — event bus handles failures)
        await self._event_bus.publish(
            MessageCreatedEvent(
                tenant_id=input_dto.tenant_id,
                payload={
                    "conversation_id": str(input_dto.conversation_id),
                    "message_id": str(assistant_message.id),
                    "role": MessageRole.ASSISTANT,
                },
            )
        )

        return SendMessageOutput(
            conversation_id=conversation.id,
            message_id=assistant_message.id,
            assistant_text=assistant_text,
            tokens_used=assistant_message.tokens_used,
        )

    def _build_llm_request(self, conversation: Conversation) -> LLMRequest:
        messages = []
        if conversation.system_prompt:
            messages.append({"role": "system", "content": conversation.system_prompt})

        for msg in conversation.get_context_window(max_messages=20):
            messages.append({"role": msg.role, "content": msg.content.text})

        return LLMRequest(
            messages=messages,
            model=self._default_model,
        )
