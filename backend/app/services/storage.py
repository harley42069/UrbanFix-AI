"""Storage service for local static files and optional Cloudinary upload."""

from __future__ import annotations

import mimetypes
import os
import shutil
import time
from pathlib import Path
from typing import Optional

from ..core.config import settings
from ..core.files import normalize_relative_output_path, outputs_root, static_output_url


class StorageService:
    """Persist output artifacts and return stable public URLs."""

    def __init__(self, base_url: Optional[str] = None) -> None:
        self._base_url = (base_url or settings.BASE_URL).rstrip("/")
        self._root = outputs_root()

    def save_bytes(
        self, relative_path: str, data: bytes, content_type: str | None = None
    ) -> str:
        """Save in-memory bytes under outputs root and return public URL."""
        normalized = normalize_relative_output_path(relative_path)
        target = self._root / normalized
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

        cloud_url = self.upload_cloudinary(target, content_type=content_type)
        if cloud_url:
            return cloud_url
        return static_output_url(normalized, base_url=self._base_url)

    def save_file(self, src_path: str | Path, dest_relative_path: str) -> str:
        """Copy a local file into outputs root and return public URL."""
        src = Path(src_path)
        if not src.exists() or not src.is_file():
            raise FileNotFoundError(f"Source file not found: {src}")

        normalized = normalize_relative_output_path(dest_relative_path)
        target = self._root / normalized
        target.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file first, then atomically replace for Windows safety
        tmp_path = target.parent / f"{target.name}.tmp_{os.getpid()}"
        
        last_exc: Exception | None = None
        for attempt in range(5):
            try:
                # Copy to temporary file
                shutil.copy2(src, tmp_path)
                # Atomic replace on Windows
                os.replace(tmp_path, target)
                last_exc = None
                break
            except (PermissionError, OSError) as exc:
                last_exc = exc
                # Clean up temp file if it exists
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass
                # Exponential backoff: 100ms, 200ms, 300ms, 400ms, 500ms
                time.sleep(0.1 * (attempt + 1))

        if last_exc:
            raise last_exc

        content_type, _ = mimetypes.guess_type(str(target))
        cloud_url = self.upload_cloudinary(target, content_type=content_type)
        if cloud_url:
            return cloud_url
        return static_output_url(normalized, base_url=self._base_url)

    def upload_cloudinary(
        self, file_path: str | Path, content_type: str | None = None
    ) -> str | None:
        """Upload to Cloudinary when configured; otherwise return None."""
        if not (
            settings.CLOUDINARY_CLOUD_NAME
            and settings.CLOUDINARY_API_KEY
            and settings.CLOUDINARY_API_SECRET
        ):
            return None

        try:
            import cloudinary
            import cloudinary.uploader

            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET,
                secure=True,
            )

            upload_result = cloudinary.uploader.upload(
                str(file_path),
                resource_type="auto",
                folder="urbanfix/outputs",
            )
            return upload_result.get("secure_url")
        except Exception:
            # Do not fail pipeline when cloud upload is unavailable.
            return None
