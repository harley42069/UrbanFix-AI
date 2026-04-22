"""Pydantic schemas for stable object detection output."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DetectionBox(BaseModel):
    """Single detection bounding box in xyxy format."""

    x1: int
    y1: int
    x2: int
    y2: int
    conf: float = Field(ge=0.0, le=1.0)
    class_id: int
    class_name: str


class DetectionResult(BaseModel):
    """Stable detection payload returned by DetectionService."""

    model_config = ConfigDict(extra="ignore", protected_namespaces=())

    model_name: str
    model_version: str
    image_width: int = 0
    image_height: int = 0
    boxes: list[DetectionBox] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
