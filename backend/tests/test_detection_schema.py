from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.schemas.detection import DetectionResult
from app.services import detection as detection_module


def test_detection_fallback_returns_valid_schema_when_model_missing(tmp_path, monkeypatch):
    image_path = Path(tmp_path) / "fallback.jpg"
    Image.new("RGB", (32, 24), color=(220, 220, 220)).save(image_path)

    monkeypatch.setattr(detection_module, "YOLO", None)
    monkeypatch.setattr(
        detection_module,
        "_YOLO_IMPORT_ERROR",
        RuntimeError("simulated missing optional dependency"),
    )

    service = detection_module.DetectionService()
    result = service.detect_problems(str(image_path), visualize=False)

    # Validate stable schema fields, ignoring backward-compatible extras.
    validated = DetectionResult.model_validate(result)

    assert validated.model_name == "yolov8"
    assert validated.image_width == 32
    assert validated.image_height == 24
    assert validated.boxes == []
    assert validated.warnings
    assert "ultralytics_not_installed" in validated.warnings[0]

    # Backward compatibility for pipeline/frontend JSON view.
    assert "detections" in result
    assert "summary" in result
    assert "statistics" in result
    assert result["total_problems"] == 0
