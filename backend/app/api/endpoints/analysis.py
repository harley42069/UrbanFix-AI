"""
Analysis Endpoint
Endpoints pour l'analyse IA des espaces urbains
"""

from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import uuid
import json

from app.core.config import settings
from app.services import (
    get_detection_service,
    get_image_generation_service,
    get_cost_estimation_service,
    get_audio_generation_service,
    get_video_generation_service,
    get_pdf_report_service,
    get_orchestrator_service
)

router = APIRouter()

# Store pour les analyses en cours (en production, utiliser Redis/DB)
analysis_store: Dict[str, Dict[str, Any]] = {}


class AnalysisRequest(BaseModel):
    """Requête d'analyse"""
    file_id: str = Field(..., description="ID du fichier uploadé")
    project_name: str = Field(..., description="Nom du projet")
    location: str = Field(..., description="Localisation (ville, quartier)")
    region: str = Field(default="Tunis", description="Région pour le calcul des coûts")
    scenario_type: str = Field(default="moderate", description="Type de scénario: conservative, moderate, innovative")
    num_scenarios: int = Field(default=3, ge=1, le=5, description="Nombre de scénarios à générer")
    confidence_threshold: float = Field(default=0.25, ge=0.1, le=0.9, description="Seuil de confiance pour la détection")
    generate_audio: bool = Field(default=True, description="Générer la narration audio")
    generate_video: bool = Field(default=True, description="Générer la vidéo de transformation")
    generate_report: bool = Field(default=True, description="Générer le rapport PDF")


class QuickAnalysisRequest(BaseModel):
    """Requête d'analyse rapide (détection + coût seulement)"""
    file_id: str = Field(..., description="ID du fichier uploadé")
    confidence_threshold: float = Field(default=0.25, ge=0.1, le=0.9, description="Seuil de confiance")
    region: str = Field(default="Tunis", description="Région pour le calcul des coûts")


class AnalysisStatus(BaseModel):
    """Statut d'une analyse"""
    analysis_id: str
    status: str  # pending, processing, completed, failed
    progress: float  # 0.0 to 1.0
    current_step: Optional[str] = None
    message: Optional[str] = None
    started_at: str
    completed_at: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


def get_file_path_from_id(file_id: str) -> Path:
    """
    Récupère le chemin du fichier depuis son ID
    
    Args:
        file_id: ID du fichier
        
    Returns:
        Chemin du fichier
        
    Raises:
        HTTPException: Si le fichier n'existe pas
    """
    uploads_dir = Path(settings.UPLOADS_DIR)
    matching_files = list(uploads_dir.glob(f"*_{file_id}.*"))
    
    if not matching_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fichier non trouvé: {file_id}"
        )
    
    return matching_files[0]


async def process_full_analysis(
    analysis_id: str,
    request: AnalysisRequest,
    file_path: Path
):
    """
    Traite une analyse complète en arrière-plan
    
    Args:
        analysis_id: ID de l'analyse
        request: Paramètres de l'analyse
        file_path: Chemin du fichier
    """
    try:
        # Mettre à jour le statut
        analysis_store[analysis_id]["status"] = "processing"
        analysis_store[analysis_id]["current_step"] = "Initialisation"
        analysis_store[analysis_id]["progress"] = 0.0
        
        # Préparer les infos du projet
        project_info = {
            "name": request.project_name,
            "location": request.location,
            "region": request.region,
            "analysis_date": datetime.now().isoformat()
        }
        
        # Obtenir l'orchestrateur
        orchestrator = get_orchestrator_service()
        
        # Callback pour le suivi de progression
        def progress_callback(step: str, progress: float, message: str = ""):
            analysis_store[analysis_id]["current_step"] = step
            analysis_store[analysis_id]["progress"] = progress
            analysis_store[analysis_id]["message"] = message
        
        # Lancer le pipeline complet
        results = orchestrator.process_complete_pipeline(
            image_path=str(file_path),
            project_info=project_info,
            scenario_type=request.scenario_type,
            num_scenarios=request.num_scenarios,
            confidence_threshold=request.confidence_threshold,
            generate_audio=request.generate_audio,
            generate_video=request.generate_video,
            generate_report=request.generate_report,
            progress_callback=progress_callback
        )
        
        # Analyse terminée
        analysis_store[analysis_id]["status"] = "completed"
        analysis_store[analysis_id]["progress"] = 1.0
        analysis_store[analysis_id]["completed_at"] = datetime.now().isoformat()
        analysis_store[analysis_id]["results"] = results
        
    except Exception as e:
        # Erreur lors de l'analyse
        analysis_store[analysis_id]["status"] = "failed"
        analysis_store[analysis_id]["error"] = str(e)
        analysis_store[analysis_id]["completed_at"] = datetime.now().isoformat()


@router.post("/full", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def start_full_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks
) -> dict:
    """
    Démarre une analyse complète (détection + scénarios + coûts + audio + video + PDF)
    
    Args:
        request: Paramètres de l'analyse
        background_tasks: Tâches en arrière-plan
        
    Returns:
        ID de l'analyse et statut
    """
    # Vérifier que le fichier existe
    file_path = get_file_path_from_id(request.file_id)
    
    # Générer un ID unique pour l'analyse
    analysis_id = str(uuid.uuid4())
    
    # Initialiser le statut
    analysis_store[analysis_id] = {
        "analysis_id": analysis_id,
        "status": "pending",
        "progress": 0.0,
        "current_step": "En attente",
        "message": "Analyse en file d'attente",
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "results": None,
        "error": None,
        "request": request.dict()
    }
    
    # Ajouter la tâche en arrière-plan
    background_tasks.add_task(
        process_full_analysis,
        analysis_id,
        request,
        file_path
    )
    
    return {
        "success": True,
        "message": "Analyse démarrée",
        "data": {
            "analysis_id": analysis_id,
            "status": "pending",
            "estimated_time": "5-30 minutes selon la configuration"
        }
    }


@router.post("/quick", response_model=dict)
async def quick_analysis(request: QuickAnalysisRequest) -> dict:
    """
    Analyse rapide (détection + estimation des coûts uniquement)
    
    Args:
        request: Paramètres de l'analyse rapide
        
    Returns:
        Résultats de la détection et estimation
    """
    # Vérifier que le fichier existe
    file_path = get_file_path_from_id(request.file_id)
    
    try:
        # Service de détection
        detection_service = get_detection_service()
        detection_results = detection_service.detect_problems(
            image_path=str(file_path),
            confidence_threshold=request.confidence_threshold,
            visualize=True
        )
        
        # Service d'estimation des coûts
        cost_service = get_cost_estimation_service()
        cost_estimation = cost_service.estimate_costs(
            detection_results=detection_results,
            scenario_type="moderate",
            region=request.region
        )
        
        return {
            "success": True,
            "message": "Analyse rapide terminée",
            "data": {
                "detection": detection_results,
                "cost_estimation": cost_estimation,
                "processing_time": detection_results.get("processing_time", 0) + 
                                  cost_estimation.get("processing_time", 0)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'analyse: {str(e)}"
        )


@router.get("/status/{analysis_id}", response_model=AnalysisStatus)
async def get_analysis_status(analysis_id: str) -> AnalysisStatus:
    """
    Récupère le statut d'une analyse
    
    Args:
        analysis_id: ID de l'analyse
        
    Returns:
        Statut de l'analyse
    """
    if analysis_id not in analysis_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analyse non trouvée"
        )
    
    return AnalysisStatus(**analysis_store[analysis_id])


@router.get("/results/{analysis_id}", response_model=dict)
async def get_analysis_results(analysis_id: str) -> dict:
    """
    Récupère les résultats complets d'une analyse
    
    Args:
        analysis_id: ID de l'analyse
        
    Returns:
        Résultats de l'analyse
    """
    if analysis_id not in analysis_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analyse non trouvée"
        )
    
    analysis = analysis_store[analysis_id]
    
    if analysis["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Analyse non terminée. Statut actuel: {analysis['status']}"
        )
    
    return {
        "success": True,
        "data": {
            "analysis_id": analysis_id,
            "results": analysis["results"],
            "started_at": analysis["started_at"],
            "completed_at": analysis["completed_at"]
        }
    }


@router.delete("/{analysis_id}", response_model=dict)
async def delete_analysis(analysis_id: str) -> dict:
    """
    Supprime une analyse et ses résultats
    
    Args:
        analysis_id: ID de l'analyse
        
    Returns:
        Confirmation de suppression
    """
    if analysis_id not in analysis_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analyse non trouvée"
        )
    
    # Supprimer du store
    del analysis_store[analysis_id]
    
    # TODO: Supprimer les fichiers générés (images, PDFs, etc.)
    
    return {
        "success": True,
        "message": "Analyse supprimée",
        "analysis_id": analysis_id
    }


@router.get("/list", response_model=dict)
async def list_analyses(
    status_filter: Optional[str] = None,
    limit: int = 50
) -> dict:
    """
    Liste toutes les analyses
    
    Args:
        status_filter: Filtrer par statut (pending, processing, completed, failed)
        limit: Nombre maximum de résultats
        
    Returns:
        Liste des analyses
    """
    analyses = list(analysis_store.values())
    
    # Filtrer par statut si demandé
    if status_filter:
        analyses = [a for a in analyses if a["status"] == status_filter]
    
    # Trier par date (plus récent en premier)
    analyses.sort(key=lambda x: x["started_at"], reverse=True)
    
    # Limiter le nombre de résultats
    analyses = analyses[:limit]
    
    return {
        "success": True,
        "data": {
            "total": len(analyses),
            "analyses": [
                {
                    "analysis_id": a["analysis_id"],
                    "status": a["status"],
                    "progress": a["progress"],
                    "current_step": a.get("current_step"),
                    "started_at": a["started_at"],
                    "completed_at": a.get("completed_at")
                }
                for a in analyses
            ]
        }
    }


@router.post("/detect-only", response_model=dict)
async def detect_only(
    file_id: str,
    confidence_threshold: float = 0.25,
    visualize: bool = True
) -> dict:
    """
    Détection seule sans autre traitement
    
    Args:
        file_id: ID du fichier
        confidence_threshold: Seuil de confiance
        visualize: Créer une image annotée
        
    Returns:
        Résultats de la détection
    """
    file_path = get_file_path_from_id(file_id)
    
    try:
        detection_service = get_detection_service()
        results = detection_service.detect_problems(
            image_path=str(file_path),
            confidence_threshold=confidence_threshold,
            visualize=visualize
        )
        
        return {
            "success": True,
            "message": "Détection terminée",
            "data": results
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la détection: {str(e)}"
        )


@router.get("/system/status", response_model=dict)
async def get_system_status() -> dict:
    """
    Récupère le statut du système (mémoire, GPU, modèles chargés)
    
    Returns:
        Statut du système
    """
    try:
        orchestrator = get_orchestrator_service()
        status_info = orchestrator.get_system_status()
        
        return {
            "success": True,
            "data": status_info
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération du statut: {str(e)}"
        )


@router.post("/system/unload-models", response_model=dict)
async def unload_models() -> dict:
    """
    Décharge tous les modèles de la mémoire
    
    Returns:
        Confirmation
    """
    try:
        orchestrator = get_orchestrator_service()
        orchestrator.unload_all_models()
        
        return {
            "success": True,
            "message": "Modèles déchargés de la mémoire"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du déchargement: {str(e)}"
        )
