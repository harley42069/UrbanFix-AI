"""Endpoints to trigger and observe async signalement processing."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...core.errors import AppValidationError, ForbiddenError, NotFoundError
from ...db.session import get_db
from ...models.signalement import Signalement, SignalementStatus
from ...models.user import User
from ...schemas.common import ApiResponse, ok
from ...schemas.scenario import normalize_scenarios_payload
from ...tasks.pipeline_tasks import enqueue_signalement_processing
from ...utils.language import detect_language
from ...schemas.signalement import InteractionMode, ProblemCategory
from ..dependencies import get_current_active_user, get_current_user_optional

router = APIRouter()


class ProcessRequest(BaseModel):
    """Corps optionnel pour déclencher le pipeline."""

    user_prompt: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Texte libre (réservé usage futur / fine-tuning).",
    )
    generate_media: bool = Field(
        default=False,
        description="Si True, génère audio + vidéo + PDF en plus de détection/scénarios/estimation.",
    )
    interaction_mode: Optional[InteractionMode] = Field(default=None)
    category: Optional[ProblemCategory] = Field(default=None)
    generate_audio: bool = Field(default=False)
    generate_video: bool = Field(default=False)
    generate_pdf: bool = Field(default=False)


def _interaction_context(signalement: Signalement) -> tuple[str, str]:
    """Resolve interaction mode and category from metadata with defaults."""
    metadata = signalement.metadata_json or {}
    mode = str(metadata.get("interaction_mode") or InteractionMode.PHOTO_ONLY.value)
    category = str(metadata.get("category") or ProblemCategory.OTHER.value)
    return mode, category


def _has_real_image(signalement: Signalement) -> bool:
    """Return True when signalement has a real persisted image input."""
    image_path = str(signalement.image_path or "")
    return bool(image_path) and not image_path.startswith("prompt://")


def _normalized_status(signalement: Signalement) -> str:
    """Normalise le statut interne vers la valeur publique."""
    if signalement.status in (SignalementStatus.REJECTED, SignalementStatus.FAILED):
        return "failed"
    return signalement.status.value


def _public_outputs(signalement: Signalement) -> dict[str, Any]:
    """Construit le bloc outputs public depuis metadata_json et colonnes dédiées."""
    metadata = signalement.metadata_json or {}
    meta_outputs = metadata.get("outputs", {})

    def _public(path: str | None) -> str | None:
        if not path:
            return None
        p = str(path).replace("\\", "/")
        idx = p.find("/outputs/")
        if idx >= 0:
            return p[idx:]
        if p.startswith("outputs/"):
            return f"/{p}"
        return p

    return {
        "annotated_image": _public(
            meta_outputs.get("annotated_image")
            or (signalement.detections_data or {}).get("annotated_image_url")
            or (signalement.detections_data or {}).get("annotated_image_path")
            or (signalement.detections_data or {}).get("annotated_image")
        ),
        # Non-breaking explicit path/url alias for annotated artifact.
        "annotated_image_path": _public(
            meta_outputs.get("annotated_image")
            or (signalement.detections_data or {}).get("annotated_image_path")
            or (signalement.detections_data or {}).get("annotated_image_url")
            or (signalement.detections_data or {}).get("annotated_image")
        ),
        "scenario_image": _public(meta_outputs.get("scenario_image")),
        # Colonnes dédiées (MVP e2e) prioritaires sur metadata
        "audio": _public(signalement.audio_url or meta_outputs.get("audio")),
        "video": _public(signalement.video_url or meta_outputs.get("video")),
        "pdf": _public(signalement.pdf_url or meta_outputs.get("pdf")),
    }


def _resolve_language(signalement: Signalement, scenarios: list[dict[str, Any]]) -> str:
    """Resolve persisted language for status payload with safe FR fallback."""
    detections = signalement.detections_data or {}
    estimations = signalement.estimations_data or {}

    lang = detections.get("language") or estimations.get("language")
    if lang in ("fr", "en"):
        return lang

    if scenarios:
        narration = scenarios[0].get("narration_text")
        return detect_language(str(narration) if narration else "")

    return "fr"


@router.post(
    "/{signalement_id}",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_processing(
    signalement_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    body: Optional[ProcessRequest] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ApiResponse[dict]:
    """Déclenche le pipeline IA asynchrone pour un signalement.

    Retourne immédiatement 202 Accepted. Utilise Celery si configuré,
    sinon FastAPI ``BackgroundTasks``.
    """
    effective = body or ProcessRequest()
    signalement = (
        db.query(Signalement)
        .filter(Signalement.id == signalement_id, Signalement.is_deleted.is_(False))
        .first()
    )
    if not signalement:
        raise NotFoundError("Signalement introuvable")

    if current_user.role != "admin" and signalement.user_id != current_user.id:
        raise ForbiddenError("Accès non autorisé")

    if signalement.status == SignalementStatus.PROCESSING:
        return ok(
            {
                "signalement_id": signalement_id,
                "queued": False,
                "status": "processing",
                "message": "Pipeline déjà en cours",
            },
            request,
        )

    # Réinitialiser l'état avant de re-lancer
    signalement.status = SignalementStatus.PENDING
    signalement.progress = 0
    signalement.current_stage = "queued"
    signalement.last_error = None
    signalement.completed_at = None
    db.add(signalement)
    db.commit()

    existing_metadata = dict(signalement.metadata_json or {})
    if effective.interaction_mode is not None:
        existing_metadata["interaction_mode"] = effective.interaction_mode.value
    if effective.category is not None:
        existing_metadata["category"] = effective.category.value
    existing_metadata["generate_audio"] = effective.generate_audio
    existing_metadata["generate_video"] = effective.generate_video
    existing_metadata["generate_pdf"] = effective.generate_pdf
    signalement.metadata_json = existing_metadata
    db.add(signalement)
    db.commit()

    interaction_mode, category = _interaction_context(signalement)
    has_image = _has_real_image(signalement)

    if interaction_mode in (
        InteractionMode.PHOTO_ONLY.value,
        InteractionMode.PHOTO_AND_PROMPT.value,
    ) and not has_image:
        raise AppValidationError("image requise pour photo_only/photo_and_prompt")

    if interaction_mode in (
        InteractionMode.PHOTO_AND_PROMPT.value,
        InteractionMode.PROMPT_ONLY.value,
    ) and not (effective.user_prompt or "").strip():
        raise AppValidationError("user_prompt requis pour photo_and_prompt/prompt_only")

    media_requested = (
        effective.generate_media
        or effective.generate_audio
        or effective.generate_video
        or effective.generate_pdf
    )

    enqueue_info = enqueue_signalement_processing(
        signalement_id,
        background_tasks,
        user_prompt=effective.user_prompt,
        interaction_mode=interaction_mode,
        category=category,
        generate_media=media_requested,
        generate_audio=effective.generate_audio,
        generate_video=effective.generate_video,
        generate_pdf=effective.generate_pdf,
    )
    return ok(
        {
            "signalement_id": signalement_id,
            "queued": True,
            "status": "pending",
            "queue_mode": enqueue_info.get("mode", "background_tasks"),
            "task_id": enqueue_info.get("task_id"),
            "generate_media": media_requested,
            "generate_audio": effective.generate_audio,
            "generate_video": effective.generate_video,
            "generate_pdf": effective.generate_pdf,
            "interaction_mode": interaction_mode,
            "category": category,
        },
        request,
    )


@router.get(
    "/{signalement_id}/status",
    response_model=ApiResponse[dict],
)
async def get_processing_status(
    signalement_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> ApiResponse[dict]:
    """Consulte le statut et les résultats du pipeline pour un signalement.

    Expose : status, progress, current_stage, last_error,
    detections/scenarios/estimations (JSON), URLs médias, completed_at.
    """
    signalement = (
        db.query(Signalement)
        .filter(Signalement.id == signalement_id, Signalement.is_deleted.is_(False))
        .first()
    )
    if not signalement:
        raise NotFoundError("Signalement introuvable")

    if current_user is not None and current_user.role != "admin" and signalement.user_id != current_user.id:
        raise ForbiddenError("Accès non autorisé")

    normalized_scenarios = normalize_scenarios_payload(
        signalement.scenarios_data,
        signalement.estimations_data,
    )
    outputs = _public_outputs(signalement)
    language = _resolve_language(signalement, normalized_scenarios)
    interaction_mode, category = _interaction_context(signalement)

    return ok(
        {
            "signalement_id": signalement_id,
            "status": _normalized_status(signalement),
            "progress": signalement.progress,
            "current_stage": signalement.current_stage,
            "stage": signalement.current_stage,
            "last_error": signalement.last_error,
            "completed_at": (
                signalement.completed_at.isoformat()
                if signalement.completed_at
                else None
            ),
            "processing_time_seconds": signalement.processing_time_seconds,
            "interaction_mode": interaction_mode,
            "category": category,
            # Stable status payload
            "results": {
                "language": language,
                "detections": signalement.detections_data,
                "detection_result": signalement.detections_data,
                "scenarios": normalized_scenarios,
                "media": outputs,
                "interaction_mode": interaction_mode,
                "category": category,
            },
            # Backward-compatible fields
            "language": language,
            "detections": signalement.detections_data,
            "detection_result": signalement.detections_data,
            "scenarios": normalized_scenarios,
            "estimations": signalement.estimations_data,
            "outputs": outputs,
            # Canal WebSocket pour suivi temps réel
            "ws_channel": f"/api/v1/ws/{signalement_id}",
        },
        request,
    )

