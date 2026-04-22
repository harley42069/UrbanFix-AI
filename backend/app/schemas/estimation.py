# app/shemas/estimation.py

"""
Schemas Pydantic Estimation
Validation données estimations coûts
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime

from ..models.estimation import ScenarioType


# ========== SCHEMAS CREATE/UPDATE ==========

class EstimationCreate(BaseModel):
    """
    Schema création estimation (interne - service IA)
    """
    signalement_id: int
    scenario_type: ScenarioType
    total_cost_min: float = Field(..., ge=0)
    total_cost_max: float = Field(..., ge=0)
    total_cost_avg: float = Field(..., ge=0)
    breakdown: Dict[str, Any]
    duration_days: Optional[int] = Field(None, ge=0)
    priority_score: Optional[float] = Field(None, ge=0, le=1)
    description: Optional[str] = None
    image_scenario_path: Optional[str] = None
    image_scenario_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class EstimationRequest(BaseModel):
    """
    Schema requête estimation (API publique)
    """
    signalement_id: int
    scenario_types: list[ScenarioType] = [
        ScenarioType.MINIMAL,
        ScenarioType.MODERATE,
        ScenarioType.PREMIUM
    ]
    generate_images: bool = True  # Générer images scénarios SDXL


# ========== SCHEMAS RESPONSE ==========

class EstimationResponse(BaseModel):
    """
    Schema réponse estimation (basique)
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    
    id: int
    signalement_id: int
    scenario_type: ScenarioType
    total_cost_min: float
    total_cost_max: float
    total_cost_avg: float
    breakdown: Dict[str, Any]
    duration_days: Optional[int]
    priority_score: Optional[float]
    description: Optional[str]
    image_scenario_path: Optional[str]
    image_scenario_url: Optional[str]
    created_at: datetime
    updated_at: datetime


class EstimationDetail(EstimationResponse):
    """
    Estimation détaillée (avec métadonnées)
    """
    metadata: Optional[Dict[str, Any]] = Field(default=None, validation_alias="metadata_json")


class EstimationComparison(BaseModel):
    """
    Comparaison 3 scénarios
    """
    minimal: Optional[EstimationResponse]
    moderate: Optional[EstimationResponse]
    premium: Optional[EstimationResponse]
    recommended: ScenarioType  # Scénario recommandé
    
    class Config:
        json_schema_extra = {
            "example": {
                "minimal": {"total_cost_avg": 500, "duration_days": 3},
                "moderate": {"total_cost_avg": 1500, "duration_days": 7},
                "premium": {"total_cost_avg": 5000, "duration_days": 15},
                "recommended": "moderate"
            }
        }
