"""
Centralized path utilities for backend runtime.

Goal:
- Avoid scattered Path(...) logic in endpoints/services.
- Keep path conventions stable across local/dev/prod.
"""

from pathlib import Path

from app.core.config import settings


# Repository layout anchors
# backend/app/core/paths.py -> parents[2] = backend
BACKEND_DIR = Path(__file__).resolve().parents[2]
APP_DIR = BACKEND_DIR / "app"


def resolve_backend_path(raw_path: str) -> Path:
    """Return an absolute path anchored to backend/ when input is relative."""
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return (BACKEND_DIR / candidate).resolve()


# Runtime folders from settings
UPLOADS_DIR = resolve_backend_path(settings.UPLOADS_DIR)
OUTPUTS_DIR = resolve_backend_path(settings.OUTPUTS_DIR)
TEMP_DIR = resolve_backend_path(settings.TEMP_DIR)
MODELS_DIR = resolve_backend_path(settings.MODELS_DIR)

# Common output subfolders
OUTPUT_DETECTIONS_DIR = OUTPUTS_DIR / "detections"
OUTPUT_SCENARIOS_DIR = OUTPUTS_DIR / "scenarios"
OUTPUT_AUDIO_DIR = OUTPUTS_DIR / "audio"
OUTPUT_VIDEOS_DIR = OUTPUTS_DIR / "videos"
OUTPUT_REPORTS_DIR = OUTPUTS_DIR / "reports"


def ensure_runtime_dirs() -> None:
    """Create runtime directories if they do not exist."""
    for path in [
        UPLOADS_DIR,
        OUTPUTS_DIR,
        TEMP_DIR,
        OUTPUT_DETECTIONS_DIR,
        OUTPUT_SCENARIOS_DIR,
        OUTPUT_AUDIO_DIR,
        OUTPUT_VIDEOS_DIR,
        OUTPUT_REPORTS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def output_path(category: str, filename: str) -> Path:
    """
    Build an output file path by category.

    Allowed categories: detections, scenarios, audio, videos, reports.
    """
    mapping = {
        "detections": OUTPUT_DETECTIONS_DIR,
        "scenarios": OUTPUT_SCENARIOS_DIR,
        "audio": OUTPUT_AUDIO_DIR,
        "videos": OUTPUT_VIDEOS_DIR,
        "reports": OUTPUT_REPORTS_DIR,
    }
    if category not in mapping:
        raise ValueError(f"Unknown output category: {category}")
    return mapping[category] / filename


__all__ = [
    "BACKEND_DIR",
    "APP_DIR",
    "UPLOADS_DIR",
    "OUTPUTS_DIR",
    "TEMP_DIR",
    "MODELS_DIR",
    "OUTPUT_DETECTIONS_DIR",
    "OUTPUT_SCENARIOS_DIR",
    "OUTPUT_AUDIO_DIR",
    "OUTPUT_VIDEOS_DIR",
    "OUTPUT_REPORTS_DIR",
    "resolve_backend_path",
    "ensure_runtime_dirs",
    "output_path",
]
