# app/api/endpoints/generation.py

"""
Endpoints Génération Images
Création scénarios réaménagement avec SDXL
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os

from ...db.session import get_db
from ...models.user import User
from ...models.signalement import Signalement
from ...models.estimation import Estimation, ScenarioType
from ...services.image_generation import ImageGenerationService
from .auth import get_current_active_user
from ...core.config import settings

router = APIRouter()


@router.post("/{signalement_id}", response_model=Dict[str, Any])
async def generate_scenarios(
    signalement_id: int,
    scenario_types: List[ScenarioType] = [ScenarioType.MINIMAL, ScenarioType.MODERATE, ScenarioType.PREMIUM],
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Génère scénarios réaménagement avec SDXL + LoRA
    
    Args:
        signalement_id: ID signalement
        scenario_types: Types scénarios à générer
        background_tasks: Tasks en arrière-plan
        db: Session database
        current_user: User connecté
        
    Returns:
        Images scénarios générées
        
    Raises:
        HTTPException 404 si signalement introuvable
    """
    # Récupérer signalement
    signalement = db.query(Signalement).filter(Signalement.id == signalement_id).first()
    
    if not signalement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signalement introuvable"
        )
    
    # Vérifier permissions
    if signalement.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )
    
    # Vérifier image existe
    if not os.path.exists(signalement.image_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image originale introuvable"
        )
    
    # Récupérer détections pour context
    detections = signalement.detections
    detected_classes = [d.class_name for d in detections]
    
    # Initialiser service génération
    generation_service = ImageGenerationService()
    generation_service.load_model()
    
    # Générer scénarios
    generated_scenarios = []
    
    for scenario_type in scenario_types:
        # Construire prompt selon type
        prompt = generation_service.build_scenario_prompt(
            detected_classes=detected_classes,
            scenario_type=scenario_type.value,
            location=f"{signalement.city}, Tunisia"
        )
        
        # Générer image
        result = generation_service.generate_from_image(
            image_path=signalement.image_path,
            prompt=prompt
        )
        
        # Sauvegarder path dans estimation si existe
        estimation = db.query(Estimation).filter(
            Estimation.signalement_id == signalement_id,
            Estimation.scenario_type == scenario_type
        ).first()
        
        if estimation:
            estimation.image_scenario_path = result["output_path"]
            db.commit()
        
        generated_scenarios.append({
            "scenario_type": scenario_type.value,
            "image_path": result["output_path"],
            "prompt": result["prompt"]
        })
    
    return {
        "success": True,
        "signalement_id": signalement_id,
        "scenarios_count": len(generated_scenarios),
        "scenarios": generated_scenarios
    }


@router.get("/{signalement_id}/scenarios", response_model=Dict[str, Any])
async def get_scenarios(
    signalement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Récupère scénarios générés d'un signalement
    
    Args:
        signalement_id: ID signalement
        db: Session database
        current_user: User connecté
        
    Returns:
        Liste scénarios avec images
    """
    # Récupérer signalement
    signalement = db.query(Signalement).filter(Signalement.id == signalement_id).first()
    
    if not signalement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signalement introuvable"
        )
    
    # Récupérer estimations avec images
    estimations = db.query(Estimation).filter(
        Estimation.signalement_id == signalement_id
    ).all()
    
    scenarios = [
        {
            "scenario_type": est.scenario_type.value,
            "image_path": est.image_scenario_path,
            "image_url": est.image_scenario_url,
            "cost_avg": est.total_cost_avg,
            "duration_days": est.duration_days
        }
        for est in estimations
        if est.image_scenario_path
    ]
    
    return {
        "success": True,
        "signalement_id": signalement_id,
        "scenarios_count": len(scenarios),
        "scenarios": scenarios
    }
