"""Centralized image upload validation helpers."""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from .config import settings

# Keep explicit list to avoid accepting exotic/unhandled formats.
ALLOWED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/tiff",
}


def validate_image_upload(file: UploadFile) -> None:
    """Validate extension + MIME + size + actual image readability (PIL)."""
    if not file or not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fichier manquant")

    ext = Path(file.filename).suffix.lower()
    allowed_ext = {e.lower() for e in settings.ALLOWED_IMAGE_EXTENSIONS}
    if ext not in allowed_ext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Extension non autorisée. Extensions acceptées: {', '.join(sorted(allowed_ext))}",
        )

    mime = (file.content_type or "").lower()
    if mime not in ALLOWED_IMAGE_MIME_TYPES or not mime.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Type MIME invalide pour une image",
        )

    # Size check using spooled file pointer.
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Fichier trop volumineux (max {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB)",
        )

    # Validate bytes are actually a readable image.
    try:
        img = Image.open(file.file)
        img.verify()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fichier image corrompu ou illisible",
        )
    finally:
        file.file.seek(0)
