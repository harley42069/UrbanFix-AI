"""
Upload Endpoint
Gestion des uploads d'images pour l'analyse
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
from pathlib import Path
import shutil
import uuid
from datetime import datetime
from typing import List
import os

from app.core.config import settings
from app.core.upload_validation import validate_image_upload

router = APIRouter()

def save_upload_file(file: UploadFile) -> dict:
    """
    Sauvegarde le fichier uploadé
    
    Args:
        file: Fichier à sauvegarder
        
    Returns:
        Dict avec les infos du fichier sauvegardé
    """
    # Générer un ID unique
    file_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Créer le nom de fichier
    file_ext = Path(file.filename).suffix
    filename = f"{timestamp}_{file_id}{file_ext}"
    
    # Créer le répertoire uploads s'il n'existe pas
    uploads_dir = Path(settings.UPLOADS_DIR)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    # Chemin complet
    file_path = uploads_dir / filename
    
    # Sauvegarder le fichier
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la sauvegarde: {str(e)}"
        )
    finally:
        file.file.close()
    
    # Vérifier la taille
    file_size = file_path.stat().st_size
    if file_size > settings.MAX_UPLOAD_SIZE:
        file_path.unlink()  # Supprimer le fichier
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Fichier trop volumineux (max {settings.MAX_UPLOAD_SIZE // (1024*1024)}MB)"
        )
    
    return {
        "file_id": file_id,
        "filename": filename,
        "original_filename": file.filename,
        "file_path": str(file_path),
        "file_size": file_size,
        "upload_time": timestamp,
        "content_type": file.content_type
    }


@router.post("/image", response_model=dict, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(..., description="Image à analyser")
) -> dict:
    """
    Upload une image pour analyse
    
    Args:
        file: Fichier image
        
    Returns:
        Informations sur le fichier uploadé
        
    Raises:
        HTTPException: Si l'upload échoue
    """
    # Valider l'image
    validate_image_upload(file)
    
    # Sauvegarder le fichier
    file_info = save_upload_file(file)
    
    return {
        "success": True,
        "message": "Image uploadée avec succès",
        "data": file_info
    }


@router.post("/images/batch", response_model=dict, status_code=status.HTTP_201_CREATED)
async def upload_images_batch(
    files: List[UploadFile] = File(..., description="Images à analyser")
) -> dict:
    """
    Upload multiple images en batch
    
    Args:
        files: Liste de fichiers images
        
    Returns:
        Informations sur les fichiers uploadés
    """
    if len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 fichiers par batch"
        )
    
    uploaded_files = []
    errors = []
    
    for file in files:
        try:
            validate_image_upload(file)
            file_info = save_upload_file(file)
            uploaded_files.append(file_info)
        except HTTPException as e:
            errors.append({
                "filename": file.filename,
                "error": e.detail
            })
        except Exception as e:
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return {
        "success": len(uploaded_files) > 0,
        "message": f"{len(uploaded_files)}/{len(files)} images uploadées",
        "data": {
            "uploaded": uploaded_files,
            "errors": errors
        }
    }


@router.delete("/{file_id}", response_model=dict)
async def delete_uploaded_file(file_id: str) -> dict:
    """
    Supprime un fichier uploadé
    
    Args:
        file_id: ID du fichier
        
    Returns:
        Confirmation de suppression
    """
    uploads_dir = Path(settings.UPLOADS_DIR)
    
    # Chercher le fichier avec cet ID
    matching_files = list(uploads_dir.glob(f"*_{file_id}.*"))
    
    if not matching_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier non trouvé"
        )
    
    file_path = matching_files[0]
    
    try:
        file_path.unlink()
        return {
            "success": True,
            "message": "Fichier supprimé avec succès",
            "file_id": file_id
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la suppression: {str(e)}"
        )


@router.get("/info/{file_id}", response_model=dict)
async def get_file_info(file_id: str) -> dict:
    """
    Récupère les informations d'un fichier uploadé
    
    Args:
        file_id: ID du fichier
        
    Returns:
        Informations sur le fichier
    """
    uploads_dir = Path(settings.UPLOADS_DIR)
    
    # Chercher le fichier
    matching_files = list(uploads_dir.glob(f"*_{file_id}.*"))
    
    if not matching_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier non trouvé"
        )
    
    file_path = matching_files[0]
    stat = file_path.stat()
    
    return {
        "success": True,
        "data": {
            "file_id": file_id,
            "filename": file_path.name,
            "file_path": str(file_path),
            "file_size": stat.st_size,
            "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat()
        }
    }
