from __future__ import annotations

from enum import Enum
from typing import Any, TYPE_CHECKING

from sqlalchemy import Enum as SQLEnum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.db.mixins import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.signalement import Signalement


def _enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class ScenarioType(str, Enum):
    MINIMAL = "minimal"
    MODERATE = "moderate"
    PREMIUM = "premium"


class Estimation(TimestampMixin, SoftDeleteMixin, BaseModel):
    __tablename__ = "estimations"

    signalement_id: Mapped[int] = mapped_column(
        ForeignKey("signalements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scenario_type: Mapped[ScenarioType] = mapped_column(
        SQLEnum(
            ScenarioType,
            name="scenario_type_enum",
            native_enum=False,
            values_callable=_enum_values,
        ),
        nullable=False,
        index=True,
    )
    total_cost_min: Mapped[float] = mapped_column(Float, nullable=False)
    total_cost_max: Mapped[float] = mapped_column(Float, nullable=False)
    total_cost_avg: Mapped[float] = mapped_column(Float, nullable=False)
    breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_scenario_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    image_scenario_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    signalement: Mapped[Signalement] = relationship("Signalement", back_populates="estimations")
