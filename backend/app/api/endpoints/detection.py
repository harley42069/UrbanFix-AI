# app/api/endpoints/detection.py

"""
Endpoints Détection IA
Analyse images avec YOLOv8
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os
from pathlib import Path

from ...db.session import get_db
from ...models.user import User
from ...models.signalement import Signalement
from ...models.detection import Detection
from ...services.detection import DetectionService
from .auth import get_current_active_user
from ...core.config import settings

router = APIRouter()


@router.post("/{signalement_id}", response_model=Dict[str, Any])
async def detect_problems(
    signalement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Lance détection YOLOv8 sur image d'un signalement
    
    Args:
        signalement_id: ID signalement à analyser
        db: Session database
        current_user: User connecté
        
    Returns:
        Résultats détection avec bounding boxes
        
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
    
    # Vérifier permissions (propriétaire ou admin)
    if signalement.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )
    
    # Vérifier image existe
    if not os.path.exists(signalement.image_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image introuvable"
        )
    
    # Initialiser service détection
    detection_service = DetectionService()
    detection_service.load_model()
    
    # Effectuer détection
    results = detection_service.detect(signalement.image_path)
    
    # Sauvegarder détections en DB
    detections_saved = []
    for det in results.get("detections", []):
        detection = Detection(
            signalement_id=signalement_id,
            class_name=det["class_name"],
            confidence=det["confidence"],
            bbox_x=det["bbox"][0],
            bbox_y=det["bbox"][1],
            bbox_width=det["bbox"][2],
            bbox_height=det["bbox"][3]
        )
        db.add(detection)
        detections_saved.append(detection)
    
    db.commit()
    
    # Mettre à jour statut signalement
    signalement.status = "processing"
    db.commit()
    
    return {
        "success": True,
        "signalement_id": signalement_id,
        "detections_count": len(detections_saved),
        "detections": results.get("detections", []),
        "summary": results.get("summary", {}),
        "image_annotated": results.get("annotated_path")
    }


@router.get("/{signalement_id}", response_model=Dict[str, Any])
async def get_detections(
    signalement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Récupère les détections existantes d'un signalement
    
    Args:
        signalement_id: ID signalement
        db: Session database
        current_user: User connecté
        
    Returns:
        Liste détections
    """
    # Récupérer signalement
    signalement = db.query(Signalement).filter(Signalement.id == signalement_id).first()
    
    if not signalement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signalement introuvable"
        )
    
    # Récupérer détections
    detections = db.query(Detection).filter(Detection.signalement_id == signalement_id).all()
    
    return {
        "success": True,
        "signalement_id": signalement_id,
        "detections_count": len(detections),
        "detections": [
            {
                "id": d.id,
                "class_name": d.class_name,
                "confidence": d.confidence,
                "bbox": [d.bbox_x, d.bbox_y, d.bbox_width, d.bbox_height],
                "created_at": d.created_at.isoformat()
            }
            for d in detections
        ]
    }
