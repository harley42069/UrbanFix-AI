"""Celery application bootstrap for UrbanFix async pipeline."""

from __future__ import annotations

from typing import Optional

from ..core.config import settings

try:
    from celery import Celery
except Exception:  # pragma: no cover - optional dependency in dev
    Celery = None  # type: ignore[assignment]


def _build_celery_app() -> Optional["Celery"]:
    """Create Celery app when dependency + broker are configured."""
    if Celery is None:
        return None

    if not settings.CELERY_BROKER_URL:
        return None

    app = Celery(
        "urbanfix",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND or settings.CELERY_BROKER_URL,
    )

    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
    )
    return app


celery_app = _build_celery_app()


def celery_is_ready() -> bool:
    """Return True when Celery can be used safely."""
    return celery_app is not None and settings.ENABLE_CELERY
