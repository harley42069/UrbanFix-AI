from __future__ import annotations

from app.services import image_generation as image_module


def _reset_singleton_state() -> None:
    cls = image_module.ImageGenerationService
    cls._txt2img_pipe = None
    cls._img2img_pipe = None
    cls._load_error = None
    cls._is_loaded = False


def test_image_generation_fallback_when_model_missing(tmp_path, monkeypatch):
    missing_lora = tmp_path / "missing_tnrenovation_lora.safetensors"
    monkeypatch.setenv("LORA_MODEL_PATH", str(missing_lora))
    monkeypatch.setenv("LORA_TRIGGER_TOKEN", "tnrenovation")

    _reset_singleton_state()
    service = image_module.ImageGenerationService()

    result = service.generate_scenarios(
        detection_results={},
        source_image_path=None,
        scenario_types=["conservateur", "modere", "innovant"],
    )

    assert isinstance(result, list)
    assert result == [] or len(result) == 3

    if result:
        for item in result:
            assert item["scenario_type"] in {"conservateur", "modere", "innovant"}
            assert item["image_path"] is None
            assert isinstance(item["prompt_used"], str) and item["prompt_used"]
            assert isinstance(item["generation_time_seconds"], float)
            assert "warning" in item and isinstance(item["warning"], str)
            assert (
                "lora_model_missing:" in item["warning"]
                or "diffusers_not_installed:" in item["warning"]
                or "torch_not_installed:" in item["warning"]
                or "sdxl_load_failed:" in item["warning"]
            )
