"""Base SQLAlchemy commune pour l'application."""

from typing import Any

from sqlalchemy import Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base déclarative SQLAlchemy 2.0."""


class BaseModel(Base):
    """Modèle de base abstrait avec clé primaire commune."""

    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    def to_dict(self) -> dict[str, Any]:
        """Convertit une instance ORM en dictionnaire plat."""
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}
