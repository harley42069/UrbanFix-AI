"""
Reports Endpoint
Endpoints pour la génération et téléchargement de rapports PDF
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
import uuid

from app.core.config import settings
from app.api.dependencies import require_role
from app.models.user import User
from app.services import get_pdf_report_service

router = APIRouter()

# Store pour les rapports (en production, utiliser DB)
reports_store: Dict[str, Dict[str, Any]] = {}


class ReportGenerationRequest(BaseModel):
    """Requête de génération de rapport"""
    analysis_id: str = Field(..., description="ID de l'analyse")
    include_executive_summary: bool = Field(default=True, description="Inclure résumé exécutif")
    include_detailed_costs: bool = Field(default=True, description="Inclure détails des coûts")
    include_technical_specs: bool = Field(default=True, description="Inclure spécifications techniques")
    include_timeline: bool = Field(default=True, description="Inclure chronologie")
    language: str = Field(default="fr", description="Langue du rapport (fr, ar, en)")


class CustomReportRequest(BaseModel):
    """Requête de rapport personnalisé"""
    project_name: str = Field(..., description="Nom du projet")
    location: str = Field(..., description="Localisation")
    detection_results: Dict[str, Any] = Field(..., description="Résultats de détection")
    scenarios: Optional[List[Dict[str, Any]]] = Field(default=None, description="Scénarios générés")
    cost_estimation: Optional[Dict[str, Any]] = Field(default=None, description="Estimation des coûts")
    additional_notes: Optional[str] = Field(default=None, description="Notes additionnelles")


async def generate_report_background(
    report_id: str,
    project_data: Dict[str, Any],
    detection_results: Dict[str, Any],
    scenarios: Optional[List[Dict[str, Any]]] = None,
    cost_estimation: Optional[Dict[str, Any]] = None
):
    """
    Génère un rapport en arrière-plan
    
    Args:
        report_id: ID du rapport
        project_data: Données du projet
        detection_results: Résultats de détection
        scenarios: Scénarios générés
        cost_estimation: Estimation des coûts
    """
    try:
        reports_store[report_id]["status"] = "generating"
        
        # Service PDF
        pdf_service = get_pdf_report_service()
        
        # Générer le rapport
        pdf_path = pdf_service.generate_complete_report(
            project_data=project_data,
            detection_results=detection_results,
            scenarios=scenarios or [],
            cost_estimation=cost_estimation
        )
        
        # Mettre à jour le statut
        reports_store[report_id]["status"] = "completed"
        reports_store[report_id]["pdf_path"] = pdf_path
        reports_store[report_id]["completed_at"] = datetime.now().isoformat()
        reports_store[report_id]["file_size"] = Path(pdf_path).stat().st_size
        
    except Exception as e:
        reports_store[report_id]["status"] = "failed"
        reports_store[report_id]["error"] = str(e)
        reports_store[report_id]["completed_at"] = datetime.now().isoformat()


@router.post("/generate", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def generate_report_from_analysis(
    request: ReportGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role(["municipality", "admin"])),
) -> dict:
    """
    Génère un rapport PDF depuis une analyse existante
    
    Args:
        request: Paramètres du rapport
        background_tasks: Tâches en arrière-plan
        
    Returns:
        ID du rapport et statut
    """
    # Import local pour éviter les imports circulaires
    from app.api.endpoints.analysis import analysis_store
    
    # Vérifier que l'analyse existe
    if request.analysis_id not in analysis_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analyse non trouvée"
        )
    
    analysis = analysis_store[request.analysis_id]
    
    # Vérifier que l'analyse est terminée
    if analysis["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Analyse non terminée. Statut: {analysis['status']}"
        )
    
    # Générer un ID unique pour le rapport
    report_id = str(uuid.uuid4())
    
    # Initialiser le rapport
    reports_store[report_id] = {
        "report_id": report_id,
        "analysis_id": request.analysis_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "pdf_path": None,
        "file_size": None,
        "error": None
    }
    
    # Extraire les données
    results = analysis["results"]
    project_data = {
        "name": analysis["request"]["project_name"],
        "location": analysis["request"]["location"],
        "region": analysis["request"]["region"],
        "analysis_date": analysis["started_at"]
    }
    
    # Ajouter la tâche en arrière-plan
    background_tasks.add_task(
        generate_report_background,
        report_id,
        project_data,
        results.get("detection", {}),
        results.get("scenarios", []),
        results.get("cost_estimation", {})
    )
    
    return {
        "success": True,
        "message": "Génération du rapport démarrée",
        "data": {
            "report_id": report_id,
            "status": "pending",
            "estimated_time": "30-60 secondes"
        }
    }


@router.post("/generate/custom", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def generate_custom_report(
    request: CustomReportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role(["municipality", "admin"])),
) -> dict:
    """
    Génère un rapport PDF personnalisé
    
    Args:
        request: Données du rapport
        background_tasks: Tâches en arrière-plan
        
    Returns:
        ID du rapport et statut
    """
    report_id = str(uuid.uuid4())
    
    # Initialiser le rapport
    reports_store[report_id] = {
        "report_id": report_id,
        "analysis_id": None,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "pdf_path": None,
        "file_size": None,
        "error": None
    }
    
    # Préparer les données du projet
    project_data = {
        "name": request.project_name,
        "location": request.location,
        "analysis_date": datetime.now().isoformat(),
        "notes": request.additional_notes
    }
    
    # Ajouter la tâche
    background_tasks.add_task(
        generate_report_background,
        report_id,
        project_data,
        request.detection_results,
        request.scenarios,
        request.cost_estimation
    )
    
    return {
        "success": True,
        "message": "Génération du rapport personnalisé démarrée",
        "data": {
            "report_id": report_id,
            "status": "pending"
        }
    }


@router.get("/status/{report_id}", response_model=dict)
async def get_report_status(
    report_id: str,
    current_user: User = Depends(require_role(["municipality", "admin"])),
) -> dict:
    """
    Récupère le statut d'un rapport
    
    Args:
        report_id: ID du rapport
        
    Returns:
        Statut du rapport
    """
    if report_id not in reports_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rapport non trouvé"
        )
    
    report = reports_store[report_id]
    
    return {
        "success": True,
        "data": {
            "report_id": report_id,
            "status": report["status"],
            "created_at": report["created_at"],
            "completed_at": report.get("completed_at"),
            "file_size": report.get("file_size"),
            "error": report.get("error")
        }
    }


@router.get("/download/{report_id}", response_class=FileResponse)
async def download_report(
    report_id: str,
    current_user: User = Depends(require_role(["municipality", "admin"])),
) -> FileResponse:
    """
    Télécharge un rapport PDF
    
    Args:
        report_id: ID du rapport
        
    Returns:
        Fichier PDF
    """
    if report_id not in reports_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rapport non trouvé"
        )
    
    report = reports_store[report_id]
    
    # Vérifier que le rapport est terminé
    if report["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rapport non prêt. Statut: {report['status']}"
        )
    
    # Vérifier que le fichier existe
    pdf_path = Path(report["pdf_path"])
    if not pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier PDF non trouvé"
        )
    
    # Retourner le fichier
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"rapport_urbanfix_{report_id[:8]}.pdf"
    )


@router.delete("/{report_id}", response_model=dict)
async def delete_report(
    report_id: str,
    current_user: User = Depends(require_role(["admin"])),
) -> dict:
    """
    Supprime un rapport
    
    Args:
        report_id: ID du rapport
        
    Returns:
        Confirmation de suppression
    """
    if report_id not in reports_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rapport non trouvé"
        )
    
    report = reports_store[report_id]
    
    # Supprimer le fichier PDF s'il existe
    if report.get("pdf_path"):
        pdf_path = Path(report["pdf_path"])
        if pdf_path.exists():
            pdf_path.unlink()
    
    # Supprimer du store
    del reports_store[report_id]
    
    return {
        "success": True,
        "message": "Rapport supprimé",
        "report_id": report_id
    }


@router.get("/list", response_model=dict)
async def list_reports(
    analysis_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(require_role(["municipality", "admin"])),
) -> dict:
    """
    Liste tous les rapports
    
    Args:
        analysis_id: Filtrer par ID d'analyse
        status_filter: Filtrer par statut
        limit: Nombre maximum de résultats
        
    Returns:
        Liste des rapports
    """
    reports = list(reports_store.values())
    
    # Filtrer par ID d'analyse
    if analysis_id:
        reports = [r for r in reports if r.get("analysis_id") == analysis_id]
    
    # Filtrer par statut
    if status_filter:
        reports = [r for r in reports if r["status"] == status_filter]
    
    # Trier par date
    reports.sort(key=lambda x: x["created_at"], reverse=True)
    
    # Limiter
    reports = reports[:limit]
    
    return {
        "success": True,
        "data": {
            "total": len(reports),
            "reports": [
                {
                    "report_id": r["report_id"],
                    "analysis_id": r.get("analysis_id"),
                    "status": r["status"],
                    "created_at": r["created_at"],
                    "completed_at": r.get("completed_at"),
                    "file_size": r.get("file_size")
                }
                for r in reports
            ]
        }
    }


@router.get("/preview/{report_id}", response_model=dict)
async def get_report_preview(
    report_id: str,
    current_user: User = Depends(require_role(["municipality", "admin"])),
) -> dict:
    """
    Récupère un aperçu du rapport (métadonnées)
    
    Args:
        report_id: ID du rapport
        
    Returns:
        Métadonnées du rapport
    """
    if report_id not in reports_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rapport non trouvé"
        )
    
    report = reports_store[report_id]
    
    if report["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rapport non terminé"
        )
    
    # Extraire les métadonnées du PDF
    pdf_path = Path(report["pdf_path"])
    
    return {
        "success": True,
        "data": {
            "report_id": report_id,
            "filename": pdf_path.name,
            "file_size": report["file_size"],
            "created_at": report["created_at"],
            "completed_at": report["completed_at"],
            "pages": "~20-30 pages",  # TODO: extraire le nombre réel de pages
            "format": "PDF A4"
        }
    }
