from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.schemas.detection import DetectionResult
from app.services import detection as detection_module


def _make_image(tmp_path: Path, name: str = "img.jpg") -> Path:
    path = tmp_path / name
    Image.new("RGB", (40, 30), color=(200, 200, 200)).save(path)
    return path


def test_detection_fallback_when_model_missing_returns_valid_schema(tmp_path, monkeypatch):
    image_path = _make_image(tmp_path)

    # Simulate ultralytics available so fallback reason is model missing.
    monkeypatch.setattr(detection_module, "YOLO", lambda _p: object())
    monkeypatch.setattr(detection_module, "_YOLO_IMPORT_ERROR", None)

    service = detection_module.DetectionService()
    service.model = None
    service.model_path = str(tmp_path / "missing_best.pt")

    result = service.detect_problems(str(image_path), visualize=False)
    parsed = DetectionResult.model_validate(result)

    assert parsed.boxes == []
    assert parsed.warnings
    assert any(msg.startswith("yolo_model_not_found:") for msg in parsed.warnings)


def test_detection_fallback_when_ultralytics_missing_returns_valid_schema(tmp_path, monkeypatch):
    image_path = _make_image(tmp_path)

    monkeypatch.setattr(detection_module, "YOLO", None)
    monkeypatch.setattr(detection_module, "_YOLO_IMPORT_ERROR", ImportError("simulated missing ultralytics"))

    service = detection_module.DetectionService()
    service.model = None

    result = service.detect_problems(str(image_path), visualize=False)
    parsed = DetectionResult.model_validate(result)

    assert parsed.boxes == []
    assert parsed.warnings
    assert "ultralytics_not_installed" in parsed.warnings
