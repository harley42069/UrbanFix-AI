from __future__ import annotations

import base64
import os
from pathlib import Path

import pytest
from groq import Groq

from app.core.config import settings


IMAGE_PATH = Path(__file__).resolve().parents[1] / "test_data" / "rdd_with_detections.jpg"
PROMPT = (
    "Analyse cette image de rue. Reponds en JSON avec: type_espace, "
    "longueur_estimee_m, largeur_rue_m, nb_poteaux_existants, "
    "surface_trottoirs_m2, surface_espaces_verts_m2, problemes_visibles, contexte"
)


def run_vision_smoke() -> str:
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is required")
    if not IMAGE_PATH.exists():
        raise FileNotFoundError(f"Image test introuvable: {IMAGE_PATH}")

    client = Groq(api_key=settings.GROQ_API_KEY)
    image_data = base64.b64encode(IMAGE_PATH.read_bytes()).decode()

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
        max_tokens=400,
        temperature=0.1,
    )
    return response.choices[0].message.content or ""


def test_groq_vision_smoke_opt_in() -> None:
    if os.getenv("RUN_VISION_TESTS") != "1":
        pytest.skip("Manual Groq vision smoke test; set RUN_VISION_TESTS=1 to run.")
    if not IMAGE_PATH.exists():
        pytest.skip(f"Missing test image: {IMAGE_PATH}")
    if not settings.GROQ_API_KEY:
        pytest.skip("GROQ_API_KEY is not configured.")

    assert run_vision_smoke().strip()


if __name__ == "__main__":
    print(run_vision_smoke())
