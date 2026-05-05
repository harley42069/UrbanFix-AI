from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum as SQLEnum, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.db.mixins import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.signalement import Signalement


def _enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class UserRole(str, Enum):
    CITIZEN = "citizen"
    MUNICIPALITY = "municipality"
    ADMIN = "admin"


class User(TimestampMixin, SoftDeleteMixin, BaseModel):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("username", name="uq_users_username"),
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(
            UserRole,
            name="user_role_enum",
            native_enum=False,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=UserRole.CITIZEN,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    signalements: Mapped[list[Signalement]] = relationship(
        "Signalement",
        back_populates="user",
        cascade="all, delete-orphan",
    )
