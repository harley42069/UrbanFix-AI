"""Async pipeline tasks for Signalement processing.

This module supports two execution modes:
1. Celery worker when broker is configured and ENABLE_CELERY=true.
2. Thread-based fallback when Celery is unavailable.

Corrections v2:
- Thread séparé au lieu de BackgroundTasks (qui ne démarre pas toujours)
- user_prompt passé à generate_scenarios pour enrichissement Groq
"""

from __future__ import annotations

import asyncio
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from sqlalchemy.orm import Session

from ..core.config import settings
from ..db.session import SessionLocal
from ..models.signalement import Signalement, SignalementStatus
from .celery_app import celery_app, celery_is_ready


# Stage progression map (0-100)
STAGE_PROGRESS: dict[str, int] = {
    "queued":     0,
    "detection":  15,
    "images":     35,
    "cost":       55,
    "audio":      70,
    "video":      85,
    "pdf":        95,
    "completed":  100,
}

_UNSET = object()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _safe_notify_signalement_updated(signalement_id: int, payload: dict[str, Any]) -> None:
    """Emit websocket update from sync code without breaking current thread."""
    try:
        from ..api.endpoints.websocket_endpoint import notify_signalement_updated
        coro = notify_signalement_updated(signalement_id, payload)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            asyncio.run(coro)
    except Exception:
        pass


def _extract_outputs(metadata_json: dict[str, Any] | None) -> dict[str, str | None]:
    outputs = (metadata_json or {}).get("outputs", {})
    return {
        "annotated_image": outputs.get("annotated_image"),
        "scenario_image":  outputs.get("scenario_image"),
        "audio":           outputs.get("audio"),
        "video":           outputs.get("video"),
        "pdf":             outputs.get("pdf"),
    }


def _public_path(path: str | None) -> str | None:
    if not path:
        return None
    normalized = path.replace("\\", "/")
    idx = normalized.find("/outputs/")
    if idx >= 0:
        return normalized[idx:]
    if normalized.startswith("outputs/"):
        return f"/{normalized}"
    return normalized


def _public_outputs(metadata_json: dict[str, Any] | None) -> dict[str, str | None]:
    raw = _extract_outputs(metadata_json)
    return {k: _public_path(v) for k, v in raw.items()}


def _mark_state(
    db: Session,
    signalement: Signalement,
    *,
    status: SignalementStatus | None = None,
    progress: int | None = None,
    stage: str | None = None,
    last_error: Any = _UNSET,
    completed_at: datetime | None = None,
    metadata_updates: dict[str, Any] | None = None,
) -> None:
    """Persist pipeline state to DB and emit websocket event."""
    if status is not None:
        signalement.status = status
    if progress is not None:
        signalement.progress = max(0, min(100, int(progress)))
    if stage is not None:
        signalement.current_stage = stage
    if completed_at is not None:
        signalement.completed_at = completed_at
    if last_error is not _UNSET:
        signalement.last_error = last_error

    metadata = signalement.metadata_json or {}
    pipeline = metadata.get("pipeline", {})
    pipeline["updated_at"] = _utcnow().isoformat()
    if status is not None:
        pipeline["status"] = signalement.status.value
    if progress is not None:
        pipeline["progress"] = signalement.progress
    if stage is not None:
        pipeline["stage"] = stage
    metadata["pipeline"] = pipeline

    if metadata_updates:
        metadata.update(metadata_updates)

    signalement.metadata_json = metadata
    db.add(signalement)
    db.commit()
    db.refresh(signalement)

    _safe_notify_signalement_updated(
        signalement.id,
        {
            "event":          "signalement.updated",
            "signalement_id": signalement.id,
            "status":         "failed" if signalement.status in (
                SignalementStatus.REJECTED, SignalementStatus.FAILED
            ) else signalement.status.value,
            "progress":       signalement.progress,
            "stage":          signalement.current_stage,
            "last_error":     signalement.last_error,
            "outputs":        _public_outputs(signalement.metadata_json),
            "completed_at":   signalement.completed_at.isoformat() if signalement.completed_at else None,
        },
    )


def _retry_call(
    fn: Callable[[], Any],
    *,
    retries: int = 3,
    backoff_seconds: float = 2.0,
    on_retry: Callable[[int, Exception], None] | None = None,
) -> Any:
    """Retry helper for external service calls."""
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if attempt >= retries:
                break
            if on_retry:
                on_retry(attempt, exc)
            time.sleep(backoff_seconds * (2 ** (attempt - 1)))
    raise last_exc if last_exc else RuntimeError("Unknown retry failure")


def run_signalement_pipeline(signalement_id: int) -> dict[str, Any]:
    """Run the AI pipeline and persist state transitions in DB."""
    db = SessionLocal()
    stage = "queued"

    try:
        signalement = (
            db.query(Signalement)
            .filter(Signalement.id == signalement_id, Signalement.is_deleted.is_(False))
            .first()
        )
        if not signalement:
            return {"ok": False, "error": "signalement_not_found"}

        _mark_state(
            db, signalement,
            status=SignalementStatus.PROCESSING,
            progress=STAGE_PROGRESS["queued"],
            stage="queued",
            last_error=None,
        )

        from ..repositories.signalement_repo import save_pipeline_results
        from ..services import (
            get_audio_generation_service,
            get_cost_estimation_service,
            get_detection_service,
            get_image_generation_service,
            get_pdf_report_service,
            get_video_generation_service,
        )

        detection_svc = get_detection_service()
        image_svc     = get_image_generation_service()
        cost_svc      = get_cost_estimation_service()
        audio_svc     = get_audio_generation_service()
        video_svc     = get_video_generation_service()
        pdf_svc       = get_pdf_report_service()

        image_path = signalement.image_path
        import shutil, tempfile
        if image_path and Path(image_path).exists():
            tmp = Path(tempfile.gettempdir()) / f"urbanfix_{signalement_id}_{int(time.time())}.jpg"
            for attempt in range(5):
                try:
                    shutil.copy2(image_path, tmp)
                    image_path = str(tmp)
                    break
                except PermissionError:
                    time.sleep(0.5)

        outputs: dict[str, Any] = {"outputs": {}}

        # 1) Detection
        stage = "detection"
        _mark_state(db, signalement, progress=STAGE_PROGRESS[stage], stage=stage)
        detection_results = detection_svc.detect_problems(
            image_path, visualize=True, process_id=signalement_id,
        )
        outputs["outputs"]["annotated_image"] = detection_results.get("annotated_image")
        save_pipeline_results(db, signalement_id, detections=detection_results)
        _mark_state(db, signalement, progress=25, stage=stage, metadata_updates=outputs)

        # 2) Scenario images (SDXL + Groq prompt enrichment)
        stage = "images"
        _mark_state(db, signalement, progress=STAGE_PROGRESS[stage], stage=stage)

        #  user_prompt récupéré depuis title+description pour enrichissement Groq
        user_prompt_for_sdxl = f"{signalement.title}\n{signalement.description or ''}"

        def _gen_images() -> Any:
            return image_svc.generate_scenarios(
                detection_results,
                base_image_path=image_path,
                num_scenarios=3,
                user_prompt=user_prompt_for_sdxl,  #  Groq enrichit le prompt
            )

        scenarios = _retry_call(
            _gen_images,
            retries=settings.EXTERNAL_SERVICE_RETRIES,
            backoff_seconds=settings.EXTERNAL_SERVICE_BACKOFF_SECONDS,
            on_retry=lambda a, e: _mark_state(
                db, signalement, stage=stage, progress=40,
                last_error={"stage": stage, "retry_attempt": a, "message": str(e)},
            ),
        )

        selected = scenarios[0] if scenarios else {}
        outputs["outputs"]["scenario_image"] = selected.get("image_path")
        _mark_state(db, signalement, progress=50, stage=stage, metadata_updates=outputs)

        # 3) Cost estimation (Groq)
        stage = "cost"
        _mark_state(db, signalement, progress=STAGE_PROGRESS[stage], stage=stage)

        def _estimate_costs() -> Any:
            return cost_svc.estimate_costs(
                detection_results=detection_results,
                scenario_type="moderate",
                region=signalement.region,
            )

        cost_result = _retry_call(
            _estimate_costs,
            retries=settings.EXTERNAL_SERVICE_RETRIES,
            backoff_seconds=settings.EXTERNAL_SERVICE_BACKOFF_SECONDS,
            on_retry=lambda a, e: _mark_state(
                db, signalement, stage=stage, progress=60,
                last_error={"stage": stage, "retry_attempt": a, "message": str(e)},
            ),
        )
        outputs["cost_estimation"] = cost_result
        _mark_state(db, signalement, progress=68, stage=stage, metadata_updates=outputs)

        # 4) Audio
        stage = "audio"
        _mark_state(db, signalement, progress=STAGE_PROGRESS[stage], stage=stage)
        audio_result = audio_svc.generate_narration(detection_results, cost_result, selected)
        if audio_result.get("success"):
            outputs["outputs"]["audio"] = audio_result.get("audio_path")
        _mark_state(db, signalement, progress=78, stage=stage, metadata_updates=outputs)

        # 5) Video
        stage = "video"
        _mark_state(db, signalement, progress=STAGE_PROGRESS[stage], stage=stage)
        scenario_image = outputs["outputs"].get("scenario_image")
        video_result = {"success": False, "error": "no scenario image"}
        if scenario_image and Path(scenario_image).exists():
            video_result = video_svc.create_transformation_video(
                before_image_path=image_path,
                after_image_path=scenario_image,
                audio_path=outputs["outputs"].get("audio"),
                include_text=True,
            )
            if video_result.get("success"):
                outputs["outputs"]["video"] = video_result.get("video_path")
        _mark_state(db, signalement, progress=90, stage=stage, metadata_updates=outputs)

        # 6) PDF
        stage = "pdf"
        _mark_state(db, signalement, progress=STAGE_PROGRESS[stage], stage=stage)
        pdf_result = pdf_svc.generate_complete_report(
            project_data={
                "title":    signalement.title,
                "location": signalement.city,
                "date":     _utcnow().strftime("%d/%m/%Y"),
            },
            detection_results=detection_results,
            scenarios=scenarios,
            cost_estimation=cost_result,
        )
        if pdf_result.get("success"):
            outputs["outputs"]["pdf"] = pdf_result.get("pdf_path")

        outputs["pipeline_results"] = {
            "detection": detection_results,
            "cost":      cost_result,
            "audio":     audio_result,
            "video":     video_result,
            "pdf":       pdf_result,
        }

        _mark_state(
            db, signalement,
            status=SignalementStatus.COMPLETED,
            progress=STAGE_PROGRESS["completed"],
            stage="completed",
            completed_at=_utcnow(),
            metadata_updates=outputs,
            last_error=None,
        )
        return {"ok": True, "signalement_id": signalement_id}

    except Exception as exc:
        try:
            signalement = (
                db.query(Signalement)
                .filter(Signalement.id == signalement_id)
                .first()
            )
            if signalement:
                _mark_state(
                    db, signalement,
                    status=SignalementStatus.FAILED,
                    stage=stage,
                    last_error={
                        "stage":   stage,
                        "message": str(exc),
                        "trace":   traceback.format_exc(limit=3),
                    },
                    completed_at=_utcnow(),
                )
        except Exception:
            pass
        return {"ok": False, "error": str(exc), "stage": stage}
    finally:
        db.close()


def process_signalement(
    signalement_id: int,
    user_prompt: str | None = None,
    generate_media: bool = False,
    interaction_mode: str = "photo_only",
    category: str = "other",
    generate_audio: bool = False,
    generate_video: bool = False,
    generate_pdf: bool = False,
) -> dict[str, Any]:
    """Entry point for pipeline execution — uses orchestrator."""
    from ..services.orchestrator import get_orchestrator_service

    db = SessionLocal()
    try:
        orchestrator = get_orchestrator_service()
        return orchestrator.process_signalement_db(
            db,
            signalement_id,
            user_prompt=user_prompt,
            generate_media=generate_media,
            interaction_mode=interaction_mode,
            category=category,
            generate_audio=generate_audio,
            generate_video=generate_video,
            generate_pdf=generate_pdf,
        )
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Enqueue helpers
# ─────────────────────────────────────────────────────────────────────────────

def _run_in_thread(
    signalement_id: int,
    user_prompt: str | None,
    generate_media: bool,
    interaction_mode: str,
    category: str,
    generate_audio: bool,
    generate_video: bool,
    generate_pdf: bool,
) -> None:
    """Exécute le pipeline dans un thread daemon séparé."""
    try:
        print(f" [Thread] Démarrage pipeline signalement {signalement_id}")
        print(f" [Thread] generate_media={generate_media}, audio={generate_audio}, pdf={generate_pdf}")
        process_signalement(
            signalement_id,
            user_prompt=user_prompt,
            generate_media=generate_media,
            interaction_mode=interaction_mode,
            category=category,
            generate_audio=generate_audio,
            generate_video=generate_video,
            generate_pdf=generate_pdf,
        )
        print(f" [Thread] Pipeline {signalement_id} terminé")
    except Exception as exc:
        print(f" [Thread] Pipeline {signalement_id} erreur: {exc}")
        traceback.print_exc()


if celery_app is not None:

    @celery_app.task(
        name="app.tasks.pipeline_tasks.process_signalement",
        bind=True,
        autoretry_for=(Exception,),
        retry_backoff=True,
        retry_kwargs={"max_retries": 3},
    )
    def process_signalement_task(
        self,
        signalement_id: int,
        user_prompt: str | None = None,
        generate_media: bool = False,
        interaction_mode: str = "photo_only",
        category: str = "other",
        generate_audio: bool = False,
        generate_video: bool = False,
        generate_pdf: bool = False,
    ) -> dict[str, Any]:
        """Celery task wrapper."""
        return process_signalement(
            signalement_id,
            user_prompt=user_prompt,
            generate_media=generate_media,
            interaction_mode=interaction_mode,
            category=category,
            generate_audio=generate_audio,
            generate_video=generate_video,
            generate_pdf=generate_pdf,
        )

    def enqueue_signalement_processing(
        signalement_id: int,
        background_tasks: Any = None,
        user_prompt: str | None = None,
        generate_media: bool = False,
        interaction_mode: str = "photo_only",
        category: str = "other",
        generate_audio: bool = False,
        generate_video: bool = False,
        generate_pdf: bool = False,
    ) -> dict[str, Any]:
        """Enqueue via Celery si disponible, sinon thread séparé."""
        if celery_is_ready():
            async_result = process_signalement_task.delay(
                signalement_id, user_prompt, generate_media,
                interaction_mode, category,
                generate_audio, generate_video, generate_pdf,
            )
            return {"queued": True, "mode": "celery", "task_id": async_result.id}

        # Thread séparé — fiable sur Windows avec uvicorn
        thread = threading.Thread(
            target=_run_in_thread,
            args=(
                signalement_id, user_prompt, generate_media,
                interaction_mode, category,
                generate_audio, generate_video, generate_pdf,
            ),
            daemon=True,
            name=f"pipeline-{signalement_id}",
        )
        thread.start()
        return {"queued": True, "mode": "background_thread", "task_id": None}

else:

    def enqueue_signalement_processing(
        signalement_id: int,
        background_tasks: Any = None,
        user_prompt: str | None = None,
        generate_media: bool = False,
        interaction_mode: str = "photo_only",
        category: str = "other",
        generate_audio: bool = False,
        generate_video: bool = False,
        generate_pdf: bool = False,
    ) -> dict[str, Any]:
        """ Thread séparé — fiable sur Windows avec uvicorn sans Celery."""
        thread = threading.Thread(
            target=_run_in_thread,
            args=(
                signalement_id, user_prompt, generate_media,
                interaction_mode, category,
                generate_audio, generate_video, generate_pdf,
            ),
            daemon=True,
            name=f"pipeline-{signalement_id}",
        )
        thread.start()
        print(f"[Thread] Pipeline {signalement_id} démarré (thread: {thread.name})")
        return {"queued": True, "mode": "background_thread", "task_id": None}