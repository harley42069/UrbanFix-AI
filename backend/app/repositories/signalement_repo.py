"""Fonctions helpers DB pour les signalements — accès bas niveau pipeline.

Ce module expose des fonctions autonomes (pas de classe) destinées au pipeline
IA. Elles effectuent toutes un ``db.commit()`` + ``db.refresh()`` pour que
l'appelant récupère l'état persisté à jour.

Note : pour les accès CRUD en dehors du pipeline, utiliser
``SignalementRepository`` dans ``signalement_repository.py``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from ..models.signalement import Signalement, SignalementStatus


def _utcnow() -> datetime:
    """Retourne l'heure UTC timezone-aware."""
    return datetime.now(timezone.utc)


def get_signalement(db: Session, signalement_id: int) -> Signalement | None:
    """Récupère un signalement actif (non supprimé) par son identifiant.

    Args:
        db: Session SQLAlchemy active.
        signalement_id: Identifiant du signalement.

    Returns:
        Instance ``Signalement`` ou ``None`` si introuvable/supprimé.
    """
    return (
        db.query(Signalement)
        .filter(
            Signalement.id == signalement_id,
            Signalement.is_deleted.is_(False),
        )
        .first()
    )


def update_signalement_status(
    db: Session,
    signalement_id: int,
    status: SignalementStatus,
    progress: int,
    stage: str,
    last_error: Any | None = None,
) -> Signalement | None:
    """Met à jour le statut / la progression du pipeline d'un signalement.

    Args:
        db: Session SQLAlchemy active.
        signalement_id: Identifiant du signalement.
        status: Nouveau statut (``SignalementStatus``).
        progress: Progression de 0 à 100.
        stage: Nom de l'étape courante (ex: ``"detection"``, ``"completed"``).
        last_error: Dictionnaire d'erreur ou ``None`` pour effacer.

    Returns:
        Instance ``Signalement`` mise à jour, ou ``None`` si introuvable.
    """
    signalement = get_signalement(db, signalement_id)
    if signalement is None:
        return None

    signalement.status = status
    signalement.progress = max(0, min(100, int(progress)))
    signalement.current_stage = stage
    signalement.last_error = last_error

    if status == SignalementStatus.COMPLETED:
        signalement.completed_at = _utcnow()
    elif status in (SignalementStatus.FAILED, SignalementStatus.PROCESSING):
        # En cas d'échec, completed_at indique l'heure de l'échec
        if status == SignalementStatus.FAILED:
            signalement.completed_at = _utcnow()

    db.add(signalement)
    db.commit()
    db.refresh(signalement)
    return signalement


def save_pipeline_results(
    db: Session,
    signalement_id: int,
    detections: dict[str, Any] | None = None,
    scenarios: dict[str, Any] | None = None,
    estimations: dict[str, Any] | None = None,
    audio_url: str | None = None,
    video_url: str | None = None,
    pdf_url: str | None = None,
    processing_time: float | None = None,
) -> Signalement | None:
    """Persiste tous les résultats IA du pipeline dans les colonnes JSON.

    N'écrase que les champs fournis ; les champs non fournis (``None``) sont
    ignorés. Utiliser explicitement ``{}`` pour effacer un champ.

    Args:
        db: Session SQLAlchemy active.
        signalement_id: Identifiant du signalement cible.
        detections: Résultats bruts de détection YOLOv8.
        scenarios: Liste des scénarios SDXL générés.
        estimations: Résultat de l'estimation de coûts Groq/Llama.
        audio_url: URL / chemin du fichier audio généré.
        video_url: URL / chemin de la vidéo générée.
        pdf_url: URL / chemin du rapport PDF.
        processing_time: Durée totale du pipeline en secondes.

    Returns:
        Instance ``Signalement`` mise à jour, ou ``None`` si introuvable.
    """
    signalement = get_signalement(db, signalement_id)
    if signalement is None:
        return None

    if detections is not None:
        signalement.detections_data = detections
    if scenarios is not None:
        signalement.scenarios_data = scenarios
    if estimations is not None:
        signalement.estimations_data = estimations
    if audio_url is not None:
        signalement.audio_url = audio_url
    if video_url is not None:
        signalement.video_url = video_url
    if pdf_url is not None:
        signalement.pdf_url = pdf_url
    if processing_time is not None:
        signalement.processing_time_seconds = processing_time

    db.add(signalement)
    db.commit()
    db.refresh(signalement)
    return signalement
