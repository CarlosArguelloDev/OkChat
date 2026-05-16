"""
OkChat — Shared Base Repository Protocol
Defines the contract that all repositories must implement.
Infrastructure adapts to this protocol; the domain depends only on it.
"""
from typing import Generic, Protocol, TypeVar
from uuid import UUID

from okchat.shared.pagination import Page, PaginationParams

EntityT = TypeVar("EntityT")


class BaseRepository(Protocol[EntityT]):
    """
    Generic async repository protocol.
    All concrete repositories implement this interface.
    The domain layer depends on this — never on SQLAlchemy.
    """

    async def get_by_id(self, entity_id: UUID) -> EntityT | None:
        """Return entity by primary key, or None if not found."""
        ...

    async def list(self, params: PaginationParams) -> Page[EntityT]:
        """Return a paginated list of entities."""
        ...

    async def save(self, entity: EntityT) -> EntityT:
        """Persist a new or updated entity. Returns the saved entity."""
        ...

    async def delete(self, entity_id: UUID) -> None:
        """Delete entity by primary key. Raises NotFoundError if missing."""
        ...
