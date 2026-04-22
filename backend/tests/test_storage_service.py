"""Unit tests for StorageService local persistence."""

from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.services.storage import StorageService


def test_save_file_creates_target_and_returns_stable_url(tmp_path, monkeypatch) -> None:
    """save_file should copy source file under outputs root and build public URL."""
    output_root = tmp_path / "outputs"
    source_file = tmp_path / "source.bin"
    source_file.write_bytes(b"hello-storage")

    monkeypatch.setattr(settings, "OUTPUTS_DIR", str(output_root))
    monkeypatch.setattr(settings, "BASE_URL", "http://localhost:8000")

    service = StorageService()
    url = service.save_file(source_file, "42/report.pdf")

    target = output_root / "42" / "report.pdf"
    assert target.exists()
    assert target.read_bytes() == b"hello-storage"
    assert url == "http://localhost:8000/static/outputs/42/report.pdf"
