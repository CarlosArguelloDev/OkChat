"""
OkChat — SQLAlchemy Declarative Base
All ORM models inherit from this base.
Provides auto-generated table names and common audit columns.
"""
import re
import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedColumn, mapped_column


def _camel_to_snake(name: str) -> str:
    """Convert CamelCase class name to snake_case table name."""
    name = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()


class Base(DeclarativeBase):
    """
    Declarative base with automatic table naming.
    UserProfile → user_profiles (pluralized snake_case)
    """

    @classmethod
    def __tablename__(cls) -> str:  # type: ignore[override]
        return _camel_to_snake(cls.__name__) + "s"


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at columns.
    server_default lets PostgreSQL handle the timestamps,
    so the app doesn't need to set them explicitly.
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    """Mixin that adds a UUID primary key column."""
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class TenantMixin:
    """Mixin that adds tenant_id for row-level multi-tenancy."""
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
