"""
OkChat — Conversation Domain Entities
Pure Python. Zero ORM. Zero FastAPI. Zero infrastructure.
This is the heart of the system.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from okchat.core.exceptions import ValidationError

if TYPE_CHECKING:
    pass


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ConversationStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


@dataclass
class MessageContent:
    """Value object: immutable message content with type."""
    text: str
    language: str = "en"

    def __post_init__(self) -> None:
        if not self.text or not self.text.strip():
            raise ValidationError(message="Message content cannot be empty")
        if len(self.text) > 32_000:
            raise ValidationError(
                message="Message too long",
                details={"max_length": 32_000, "actual": len(self.text)},
            )
        self.text = self.text.strip()


@dataclass
class Message:
    """
    A single message within a conversation.
    Immutable after creation (domain rule: messages are never edited).
    """
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: MessageRole
    content: MessageContent
    created_at: datetime
    metadata: dict = field(default_factory=dict)
    tokens_used: int | None = None

    @classmethod
    def create(
        cls,
        conversation_id: uuid.UUID,
        role: MessageRole,
        text: str,
        language: str = "en",
        metadata: dict | None = None,
    ) -> "Message":
        return cls(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            role=role,
            content=MessageContent(text=text, language=language),
            created_at=datetime.now(UTC),
            metadata=metadata or {},
        )


@dataclass
class Conversation:
    """
    Aggregate root for the conversation bounded context.
    All business rules for conversations live here.
    """
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    channel: str          # "web", "whatsapp", "telegram", "discord", "voice"
    status: ConversationStatus
    messages: list[Message]
    created_at: datetime
    updated_at: datetime
    system_prompt: str | None = None
    metadata: dict = field(default_factory=dict)

    # Domain rule: max messages before archiving
    MAX_MESSAGES = 1000

    @classmethod
    def create(
        cls,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        channel: str,
        system_prompt: str | None = None,
    ) -> "Conversation":
        now = datetime.now(UTC)
        return cls(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            channel=channel,
            status=ConversationStatus.ACTIVE,
            messages=[],
            created_at=now,
            updated_at=now,
            system_prompt=system_prompt,
        )

    def add_message(self, role: MessageRole, text: str, **kwargs) -> Message:
        """Domain method: adds a message with business rule enforcement."""
        if self.status != ConversationStatus.ACTIVE:
            raise ValidationError(
                message="Cannot add messages to an inactive conversation",
                details={"status": self.status},
            )

        if len(self.messages) >= self.MAX_MESSAGES:
            raise ValidationError(
                message="Conversation has reached maximum message limit",
                details={"max": self.MAX_MESSAGES},
            )

        message = Message.create(
            conversation_id=self.id,
            role=role,
            text=text,
            **kwargs,
        )
        self.messages.append(message)
        self.updated_at = datetime.now(UTC)
        return message

    def archive(self) -> None:
        if self.status == ConversationStatus.DELETED:
            raise ValidationError(message="Cannot archive a deleted conversation")
        self.status = ConversationStatus.ARCHIVED
        self.updated_at = datetime.now(UTC)

    def get_context_window(self, max_messages: int = 20) -> list[Message]:
        """Return the last N messages for LLM context."""
        return self.messages[-max_messages:]
