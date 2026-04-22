"""Test storage service atomic file operations for Windows compatibility."""

from __future__ import annotations

from pathlib import Path

from app.services.storage import StorageService


def test_storage_atomic_replace_creates_target(tmp_path, monkeypatch):
    """Verify save_file() creates target via atomic os.replace()."""
    from app.core.config import settings

    # Mock output directory
    monkeypatch.setattr(settings, "OUTPUT_DIR", str(tmp_path / "outputs"))
    monkeypatch.setattr(settings, "BASE_URL", "http://localhost:8000")
    monkeypatch.setattr(settings, "CLOUDINARY_CLOUD_NAME", None)  # Disable Cloudinary

    # Create source file
    src_file = tmp_path / "source.jpg"
    src_file.write_bytes(b"test image data")

    storage = StorageService()
    result_url = storage.save_file(src_file, "process/123/test_image.jpg")

    # Verify file was created at target
    target_path = tmp_path / "outputs" / "process" / "123" / "test_image.jpg"
    assert target_path.exists()
    assert target_path.read_bytes() == b"test image data"

    # Verify no .tmp files left behind
    tmp_files = list((tmp_path / "outputs").glob("**/*.tmp*"))
    assert len(tmp_files) == 0

    # Verify URL was returned
    assert "process/123/test_image.jpg" in result_url


def test_storage_handles_permission_error_retry(tmp_path, monkeypatch):
    """Verify save_file() retries on PermissionError and eventually succeeds."""
    from app.core.config import settings
    import shutil as shutil_module

    # Mock output directory
    monkeypatch.setattr(settings, "OUTPUT_DIR", str(tmp_path / "outputs"))
    monkeypatch.setattr(settings, "BASE_URL", "http://localhost:8000")
    monkeypatch.setattr(settings, "CLOUDINARY_CLOUD_NAME", None)

    # Create source file
    src_file = tmp_path / "source.jpg"
    src_file.write_bytes(b"test image data")

    storage = StorageService()

    # Simulate one failure then success
    call_count = {"value": 0}
    original_copy2 = shutil_module.copy2

    def copy2_with_simulated_failure(src, dst):
        call_count["value"] += 1
        if call_count["value"] == 1:
            raise PermissionError("Simulated lock")
        return original_copy2(src, dst)

    monkeypatch.setattr(shutil_module, "copy2", copy2_with_simulated_failure)

    result_url = storage.save_file(src_file, "process/456/test_image.jpg")

    # Verify file was created after retry
    target_path = tmp_path / "outputs" / "process" / "456" / "test_image.jpg"
    assert target_path.exists()
    assert call_count["value"] > 1  # Ensure retry happened
