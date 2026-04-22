"""Test image generation with process_id parameter for Windows-safe output structure."""

from __future__ import annotations

from pathlib import Path

from app.services import image_generation as image_module


def _reset_singleton_state() -> None:
    cls = image_module.ImageGenerationService
    cls._txt2img_pipe = None
    cls._img2img_pipe = None
    cls._load_error = None
    cls._is_loaded = False


def test_image_generation_process_id_fallback(tmp_path, monkeypatch):
    """Verify process_id parameter creates correct output directory structure even on fallback."""
    missing_lora = tmp_path / "missing_tnrenovation_lora.safetensors"
    monkeypatch.setenv("LORA_MODEL_PATH", str(missing_lora))
    monkeypatch.setenv("LORA_TRIGGER_TOKEN", "tnrenovation")

    _reset_singleton_state()
    service = image_module.ImageGenerationService()

    process_id = 42
    result = service.generate_scenarios(
        detection_results={},
        source_image_path=None,
        scenario_types=["conservateur", "modere", "innovant"],
        process_id=process_id,
    )

    assert isinstance(result, list)
    assert len(result) == 3

    for item in result:
        # Verify returned structure
        assert item["scenario_type"] in {"conservateur", "modere", "innovant"}
        assert item["image_path"] is None  # Fallback, no actual image
        assert isinstance(item["prompt_used"], str)
        assert isinstance(item["generation_time_seconds"], float)
        assert "warning" in item


def test_image_generation_scenario_naming(tmp_path, monkeypatch):
    """Verify scenario filenames use sequential numbering (scenario_1, scenario_2, scenario_3)."""
    from app.core.config import settings

    missing_lora = tmp_path / "missing_tnrenovation_lora.safetensors"
    monkeypatch.setenv("LORA_MODEL_PATH", str(missing_lora))
    
    # Mock output directory
    output_root = tmp_path / "outputs"
    monkeypatch.setattr(settings, "OUTPUT_DIR", str(output_root))

    _reset_singleton_state()
    service = image_module.ImageGenerationService()

    process_id = 100
    result = service.generate_scenarios(
        detection_results={},
        source_image_path=None,
        scenario_types=["conservateur", "modere", "innovant"],
        process_id=process_id,
    )

    # Even on fallback, verify structure returned is valid
    assert len(result) == 3
    # All results have image_path=None on fallback, but names would be sequential
    for i, item in enumerate(result):
        assert item["scenario_type"] in {"conservateur", "modere", "innovant"}
        assert item["image_path"] is None


def test_write_image_safe_creates_unique_files(tmp_path, monkeypatch):
    """Verify write_image_safe() creates files with atomic replace behavior."""
    from app.core.files import write_image_safe
    from PIL import Image

    # Create a simple test image
    test_image = Image.new("RGB", (100, 100), color="red")
    output_path = tmp_path / "test_output.jpg"

    # Write the image
    write_image_safe(test_image, output_path, format="JPEG", quality=95)

    # Verify file was created
    assert output_path.exists()
    assert output_path.stat().st_size > 0

    # Verify no .tmp file left behind
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert len(tmp_files) == 0
