from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SQLEnum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.db.mixins import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.detection import Detection
    from app.models.estimation import Estimation
    from app.models.user import User


def _enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class SignalementStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class Signalement(TimestampMixin, SoftDeleteMixin, BaseModel):
    __tablename__ = "signalements"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[SignalementStatus] = mapped_column(
        SQLEnum(
            SignalementStatus,
            name="signalement_status_enum",
            native_enum=False,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=SignalementStatus.PENDING,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_error: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    detections_data: Mapped[dict[str, Any] | None] = mapped_column("detections", JSON, nullable=True)
    scenarios_data: Mapped[Any | None] = mapped_column("scenarios", JSON, nullable=True)
    estimations_data: Mapped[dict[str, Any] | None] = mapped_column("estimations", JSON, nullable=True)

    audio_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    processing_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="signalements")
    detections: Mapped[list[Detection]] = relationship(
        "Detection",
        back_populates="signalement",
        cascade="all, delete-orphan",
    )
    estimations: Mapped[list[Estimation]] = relationship(
        "Estimation",
        back_populates="signalement",
        cascade="all, delete-orphan",
    )
