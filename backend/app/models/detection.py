from __future__ import annotations

from typing import Any, TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.db.mixins import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.signalement import Signalement


class Detection(TimestampMixin, SoftDeleteMixin, BaseModel):
    __tablename__ = "detections"

    signalement_id: Mapped[int] = mapped_column(
        ForeignKey("signalements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    class_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_x: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_width: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_height: Mapped[float] = mapped_column(Float, nullable=False)
    image_annotated_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    signalement: Mapped[Signalement] = relationship("Signalement", back_populates="detections")
