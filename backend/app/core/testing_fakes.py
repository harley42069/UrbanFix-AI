"""Données déterministes pour les tests offline du pipeline UrbanFix AI.

Ce module centralise toutes les fausses réponses de services IA utilisées
en mode test (``mock_services=True`` dans l'orchestrateur, ou monkeypatching
direct dans les fixtures pytest). Les valeurs sont **immuables** : ne jamais
les modifier en place dans un test, utiliser ``dict.copy()`` si nécessaire.

Usage::

    from app.core.testing_fakes import (
        FAKE_DETECTION_RESULT,
        FAKE_SCENARIOS,
        FAKE_COST_ESTIMATION,
        FAKE_AUDIO_RESULT,
        FAKE_VIDEO_RESULT,
        FAKE_PDF_RESULT,
    )

Note:
    Ce module ne doit PAS être importé dans du code de production ; il est
    destiné exclusivement aux tests et à l'orchestrateur en mode mock.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Détection (YOLOv8)
# ---------------------------------------------------------------------------

FAKE_DETECTION_RESULT: dict = {
    "total_problems": 2,
    "summary": {"route_degradee": 1, "trottoir_abime": 1},
    "detections": [
        {
            "class_name": "route_degradee",
            "confidence": 0.95,
            "bbox": [0.1, 0.1, 0.5, 0.5],
        },
        {
            "class_name": "trottoir_abime",
            "confidence": 0.87,
            "bbox": [0.6, 0.1, 0.9, 0.4],
        },
    ],
    "annotated_image": "/tmp/urbanfix_fake_annotated.jpg",
}
"""Résultat de détection déterministe : 2 problèmes, aucun fichier réel."""

# ---------------------------------------------------------------------------
# Scénarios (SDXL via Replicate)
# ---------------------------------------------------------------------------

FAKE_SCENARIOS: list[dict] = [
    {
        "type": "minimal",
        "image_path": "/tmp/urbanfix_fake_scenario_0.png",
        "prompt": "minimal urban fix",
        "description": "Réparation minimale : colmatage des fissures existantes.",
    },
    {
        "type": "moderate",
        "image_path": "/tmp/urbanfix_fake_scenario_1.png",
        "prompt": "moderate urban renovation",
        "description": "Rénovation modérée : reprise complète de la chaussée.",
    },
    {
        "type": "premium",
        "image_path": "/tmp/urbanfix_fake_scenario_2.png",
        "prompt": "premium urban upgrade",
        "description": "Mise à niveau premium : voirie complète avec aménagement paysager.",
    },
]
"""Trois scénarios de réaménagement déterministes (types minimal/moderate/premium)."""

# ---------------------------------------------------------------------------
# Estimation des coûts (Llama 3 via Groq)
# ---------------------------------------------------------------------------

FAKE_COST_ESTIMATION: dict = {
    "total_min": 5_000.0,
    "total_max": 15_000.0,
    "total_cost_tnd": 10_000.0,
    "total_avg": 10_000.0,
    "breakdown": {
        "route_degradee": {"unit_cost": 6_000.0, "count": 1, "cost": 6_000.0},
        "trottoir_abime": {"unit_cost": 4_000.0, "count": 1, "cost": 4_000.0},
    },
    "duration_days": 14,
    "priority_score": 0.75,
    "scenario_type": "moderate",
    "region": "Tunis",
    "description": "Estimation fictive pour tests offline.",
}
"""Estimation de coût déterministe (10 000 TND, 2 postes de travaux)."""

# ---------------------------------------------------------------------------
# Narration audio (Bark TTS)
# ---------------------------------------------------------------------------

FAKE_AUDIO_RESULT: dict = {
    "success": True,
    "audio_path": "/tmp/urbanfix_fake_audio.wav",
    "duration_seconds": 12,
    "voice_preset": "v2/fr_speaker_1",
}
"""Résultat de génération audio fictif (succès, 12 secondes)."""

# ---------------------------------------------------------------------------
# Vidéo de transformation (SVD + MoviePy)
# ---------------------------------------------------------------------------

FAKE_VIDEO_RESULT: dict = {
    "success": True,
    "video_path": "/tmp/urbanfix_fake_video.mp4",
    "duration_seconds": 8,
    "frame_count": 120,
}
"""Résultat de génération vidéo fictif (succès, 8 secondes)."""

# ---------------------------------------------------------------------------
# Rapport PDF (ReportLab)
# ---------------------------------------------------------------------------

FAKE_PDF_RESULT: dict = {
    "success": True,
    "pdf_path": "/tmp/urbanfix_fake_report.pdf",
    "file_size_mb": 0.2,
    "page_count": 4,
}
"""Résultat de génération PDF fictif (succès, 4 pages, 0.2 Mo)."""
