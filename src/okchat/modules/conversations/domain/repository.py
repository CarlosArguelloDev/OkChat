"""
OkChat — Conversation Repository Protocol
The domain declares what it needs. Infrastructure fulfills it.
"""
from typing import Protocol
from uuid import UUID

from okchat.modules.conversations.domain.entities import Conversation
from okchat.shared.pagination import Page, PaginationParams


class ConversationRepository(Protocol):
    """
    The domain's contract for persisting conversations.
    Concrete implementation lives in infrastructure/.
    """

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        """Fetch conversation with all messages. Returns None if not found."""
        ...

    async def list_by_user(
        self,
        user_id: UUID,
        tenant_id: UUID,
        params: PaginationParams,
    ) -> Page[Conversation]:
        """List conversations for a user within a tenant."""
        ...

    async def save(self, conversation: Conversation) -> Conversation:
        """Insert or update a conversation and its messages."""
        ...

    async def delete(self, conversation_id: UUID, tenant_id: UUID) -> None:
        """Soft-delete a conversation."""
        ...
