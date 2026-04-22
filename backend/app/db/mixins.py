"""Mixins SQLAlchemy réutilisables (timestamps UTC + soft delete)."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    """Retourne l'heure UTC timezone-aware."""
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Ajoute created_at/updated_at avec UTC."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class SoftDeleteMixin:
    """Ajoute suppression logique cohérente."""

    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
