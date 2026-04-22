"""Filesystem helpers for output storage and stable URL construction."""

from __future__ import annotations

import os
import time
from pathlib import Path, PurePosixPath

from .config import settings


STATIC_OUTPUT_PREFIX = "/static/outputs"


def ensure_dir(path: Path) -> Path:
    """Create directory if missing and return the same path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def outputs_root() -> Path:
    """Return absolute outputs root directory."""
    root = Path(settings.OUTPUTS_DIR)
    if not root.is_absolute():
        root = (Path.cwd() / root).resolve()
    return ensure_dir(root)


def normalize_relative_output_path(relative_path: str) -> str:
    """Normalize and validate an output-relative path.

    Prevents path traversal outside outputs root.
    """
    normalized = str(PurePosixPath(relative_path.replace("\\", "/"))).lstrip("/")
    if not normalized or normalized.startswith("..") or "/../" in normalized:
        raise ValueError("Invalid relative output path")
    return normalized


def signalement_output_dir(signalement_id: int) -> Path:
    """Return and ensure output folder for one signalement."""
    return ensure_dir(outputs_root() / str(signalement_id))


def static_output_url(relative_path: str, base_url: str | None = None) -> str:
    """Build a public absolute URL under /static/outputs."""
    normalized = normalize_relative_output_path(relative_path)
    host = (base_url or settings.BASE_URL).rstrip("/")
    return f"{host}{STATIC_OUTPUT_PREFIX}/{normalized}"


def write_image_safe(image: object, output_path: Path | str, *, format: str = "JPEG", quality: int = 95) -> None:
    """Write PIL Image to disk safely on Windows with atomic replace.
    
    Writes to temp file first, then atomically replaces target.
    Retries 3 times on PermissionError/WinError 32.
    
    Args:
        image: PIL Image object with save() method
        output_path: Target file path
        format: PIL Image format (default JPEG)
        quality: JPEG quality 0-100 (default 95)
        
    Raises:
        OSError: If write fails after 3 retries
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    tmp_path = output_path.parent / f"{output_path.name}.tmp"
    
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            # Write to temporary file first
            image.save(tmp_path, format=format, quality=quality)
            # Atomic replace on Windows
            os.replace(tmp_path, output_path)
            return
        except (PermissionError, OSError) as exc:
            last_exc = exc
            # Clean up temp file if it exists
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            # Exponential backoff: 100ms, 200ms, 400ms
            time.sleep(0.1 * (2 ** attempt))
    
    if last_exc:
        raise last_exc
