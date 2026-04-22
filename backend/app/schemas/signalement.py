# app/shemas/signalement.py

"""
Schemas Pydantic Signalement
Validation données signalements espaces urbains
"""

import enum
from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..models.signalement import SignalementStatus
from .user import UserResponse


# ========== SCHEMAS CREATE/UPDATE ==========


class InteractionMode(str, enum.Enum):
    """Supported interaction modes for signalement processing."""

    PHOTO_ONLY = "photo_only"
    PHOTO_AND_PROMPT = "photo_and_prompt"
    PROMPT_ONLY = "prompt_only"


class ProblemCategory(str, enum.Enum):
    """Supported problem categories for MVP metadata classification."""

    ROADS = "roads"
    SIDEWALK = "sidewalk"
    LIGHTING = "lighting"
    WASTE = "waste"
    DRAINAGE = "drainage"
    OTHER = "other"

class SignalementCreate(BaseModel):
    """
    Schema création signalement
    """
    title: str = Field(..., min_length=5, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: Optional[str] = Field(None, max_length=500)
    city: str = Field(..., min_length=2, max_length=100)
    region: str = Field(..., min_length=2, max_length=100)
    metadata: Optional[Dict[str, Any]] = None


class SignalementUpdate(BaseModel):
    """
    Schema mise à jour signalement
    """
    title: Optional[str] = Field(None, min_length=5, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    address: Optional[str] = Field(None, max_length=500)
    status: Optional[SignalementStatus] = None


# ========== SCHEMAS RESPONSE ==========

class SignalementResponse(BaseModel):
    """
    Schema réponse signalement (basique)
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    
    id: int
    title: str
    description: Optional[str]
    image_path: str
    image_url: Optional[str]
    latitude: float
    longitude: float
    address: Optional[str]
    city: str
    region: str
    status: SignalementStatus
    progress: int = 0
    current_stage: Optional[str] = None
    last_error: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None

    # Pipeline résultats (JSON dénormalisé MVP)
    detections_data: Optional[Dict[str, Any]] = None
    scenarios_data: Optional[Any] = None
    estimations_data: Optional[Dict[str, Any]] = None

    # URLs médias générés
    audio_url: Optional[str] = None
    video_url: Optional[str] = None
    pdf_url: Optional[str] = None
    processing_time_seconds: Optional[float] = None

    user_id: int
    metadata: Optional[Dict[str, Any]] = Field(default=None, validation_alias="metadata_json")
    created_at: datetime
    updated_at: datetime


class SignalementDetail(SignalementResponse):
    """
    Schema signalement détaillé (avec relations)
    """
    user: UserResponse
    detections_count: int = 0
    estimations_count: int = 0


class SignalementList(BaseModel):
    """
    Schema liste paginated signalements
    """
    items: List[SignalementResponse]
    total: int
    page: int
    page_size: int
    pages: int


class PromptSignalementCreate(BaseModel):
    """JSON payload for prompt-only signalement creation."""

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    interaction_mode: InteractionMode = Field(default=InteractionMode.PROMPT_ONLY)
    category: ProblemCategory
    user_prompt: Optional[str] = Field(default=None, max_length=2000)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    generate_audio: bool = Field(default=False)
    generate_video: bool = Field(default=False)
    generate_pdf: bool = Field(default=False)

    @model_validator(mode="after")
    def validate_mode_requirements(self) -> "PromptSignalementCreate":
        """Validate required prompt/image constraints by mode for JSON payload."""
        prompt = (self.user_prompt or "").strip()

        if self.interaction_mode == InteractionMode.PROMPT_ONLY and not prompt:
            raise ValueError("user_prompt est requis en mode prompt_only")

        if self.interaction_mode == InteractionMode.PHOTO_AND_PROMPT and not prompt:
            raise ValueError("user_prompt est requis en mode photo_and_prompt")

        return self
