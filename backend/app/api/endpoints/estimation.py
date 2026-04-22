# app/api/endpoints/estimation.py

"""
Endpoints Estimation Coûts
Calcul estimations avec Llama 3.1 via Groq
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from ...db.session import get_db
from ...models.user import User
from ...models.signalement import Signalement
from ...models.detection import Detection
from ...models.estimation import Estimation, ScenarioType
from ...schemas.estimation import (
    EstimationRequest,
    EstimationResponse,
    EstimationDetail,
    EstimationComparison
)
from ...schemas.common import ApiResponse, ok
from ...core.errors import AppValidationError, ForbiddenError, NotFoundError
from ...services.cost_estimation import CostEstimationService
from .auth import get_current_active_user
from ...core.config import settings

router = APIRouter()


@router.post("/{signalement_id}", response_model=ApiResponse[EstimationComparison])
async def estimate_costs(
    signalement_id: int,
    request_data: EstimationRequest,
    request: Request,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Générer estimations coûts pour un signalement.
    Retourne ``ApiResponse[EstimationComparison]``.
    """
    signalement = db.query(Signalement).filter(Signalement.id == signalement_id).first()
    if not signalement:
        raise NotFoundError("Signalement introuvable")

    if signalement.user_id != current_user.id and current_user.role != "admin":
        raise ForbiddenError("Accès non autorisé")

    detections = db.query(Detection).filter(Detection.signalement_id == signalement_id).all()
    if not detections:
        raise AppValidationError("Aucune détection trouvée. Lancez d'abord l'analyse IA.")
    
    # Préparer résultats détections pour service
    detection_results = {
        "detections": [
            {
                "class_name": d.class_name,
                "confidence": d.confidence,
                "bbox": [d.bbox_x, d.bbox_y, d.bbox_width, d.bbox_height]
            }
            for d in detections
        ],
        "summary": {}
    }
    
    # Calculer summary
    for d in detections:
        if d.class_name not in detection_results["summary"]:
            detection_results["summary"][d.class_name] = 0
        detection_results["summary"][d.class_name] += 1
    
    # Initialiser service estimation
    estimation_service = CostEstimationService()
    estimation_service._init_client()
    
    # Générer estimations pour chaque scénario
    estimations = {}
    
    for scenario_type in request_data.scenario_types:
        # Calculer estimation
        result = estimation_service.estimate_costs(
            detection_results=detection_results,
            scenario_type=scenario_type.value,
            region=signalement.region
        )
        
        # Sauvegarder en DB
        estimation = Estimation(
            signalement_id=signalement_id,
            scenario_type=scenario_type,
            total_cost_min=result["total_min"],
            total_cost_max=result["total_max"],
            total_cost_avg=result["total_avg"],
            breakdown=result["breakdown"],
            duration_days=result.get("duration_days"),
            priority_score=result.get("priority_score"),
            description=result.get("description")
        )
        
        db.add(estimation)
        db.flush()  # Pour obtenir ID
        
        estimations[scenario_type.value] = estimation
    
    db.commit()

    recommended = ScenarioType.MODERATE

    comparison = {
        "minimal": EstimationDetail.model_validate(estimations["minimal"]) if estimations.get("minimal") else None,
        "moderate": EstimationDetail.model_validate(estimations["moderate"]) if estimations.get("moderate") else None,
        "premium": EstimationDetail.model_validate(estimations["premium"]) if estimations.get("premium") else None,
        "recommended": recommended,
    }
    return ok(comparison, request)


@router.get("/{signalement_id}", response_model=List[EstimationResponse])
async def get_estimations(
    signalement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Récupérer estimations existantes d'un signalement
    
    Args:
        signalement_id: ID signalement
        db: Session database
        current_user: User connecté
        
    Returns:
        Liste estimations
    """
    # Récupérer signalement
    signalement = db.query(Signalement).filter(Signalement.id == signalement_id).first()
    
    if not signalement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signalement introuvable"
        )
    
    # Récupérer estimations
    estimations = db.query(Estimation).filter(
        Estimation.signalement_id == signalement_id
    ).all()
    
    return estimations


@router.get("/{signalement_id}/compare", response_model=ApiResponse[EstimationComparison])
async def compare_scenarios(
    signalement_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Comparer les 3 scénarios d'un signalement.
    Retourne ``ApiResponse[EstimationComparison]``.
    """
    signalement = db.query(Signalement).filter(Signalement.id == signalement_id).first()
    if not signalement:
        raise NotFoundError("Signalement introuvable")
    
    # Récupérer estimations par type
    minimal = db.query(Estimation).filter(
        Estimation.signalement_id == signalement_id,
        Estimation.scenario_type == ScenarioType.MINIMAL
    ).first()
    
    moderate = db.query(Estimation).filter(
        Estimation.signalement_id == signalement_id,
        Estimation.scenario_type == ScenarioType.MODERATE
    ).first()
    
    premium = db.query(Estimation).filter(
        Estimation.signalement_id == signalement_id,
        Estimation.scenario_type == ScenarioType.PREMIUM
    ).first()
    
    if not any([minimal, moderate, premium]):
        raise NotFoundError("Aucune estimation trouvée. Générez d'abord les estimations.")

    recommended = ScenarioType.MODERATE
    if moderate and moderate.priority_score:
        if moderate.priority_score > 0.7:
            recommended = ScenarioType.PREMIUM
        elif moderate.priority_score < 0.3:
            recommended = ScenarioType.MINIMAL

    comparison = {
        "minimal": EstimationDetail.model_validate(minimal) if minimal else None,
        "moderate": EstimationDetail.model_validate(moderate) if moderate else None,
        "premium": EstimationDetail.model_validate(premium) if premium else None,
        "recommended": recommended,
    }
    return ok(comparison, request)


@router.delete("/{estimation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_estimation(
    estimation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Supprimer une estimation
    
    Args:
        estimation_id: ID estimation
        db: Session database
        current_user: User connecté
        
    Returns:
        Aucun contenu (204)
    """
    estimation = db.query(Estimation).filter(Estimation.id == estimation_id).first()
    
    if not estimation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estimation introuvable"
        )
    
    # Vérifier permissions
    signalement = estimation.signalement
    if signalement.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )
    
    db.delete(estimation)
    db.commit()
    
    return None
