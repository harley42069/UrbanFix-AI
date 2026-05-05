# app/services/audio_generation.py

"""
Service Génération Audio - Bark TTS
Génère narration vocale description projet réaménagement

Corrections v2:
- Mapping classes RDD2022 dans labels
- Fallback numpy/scipy gracieux
- Nom fichier audio unique (timestamp)
- Fallback complet si Bark indisponible
"""

from __future__ import annotations

import os
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# numpy / scipy avec fallback
try:
    import numpy as np
    from scipy.io import wavfile
    NUMPY_AVAILABLE = True
except ImportError:
    np = None       # type: ignore[assignment]
    wavfile = None  # type: ignore[assignment]
    NUMPY_AVAILABLE = False
    warnings.warn("numpy/scipy non installés. Audio generation indisponible.")

# Bark avec fallback
try:
    from bark import SAMPLE_RATE, generate_audio, preload_models
    BARK_AVAILABLE = True
except Exception as exc:
    BARK_AVAILABLE = False
    SAMPLE_RATE = 24000
    warnings.warn(
        "Bark TTS non disponible. "
        "Installez avec: pip install git+https://github.com/suno-ai/bark.git "
        f"ou vérifiez les dépendances runtime. Erreur: {exc}"
    )

from ..core.config import settings


# ═══════════════════════════════════════════════════════
# Mapping classes RDD2022 → labels audio
# ═══════════════════════════════════════════════════════

_LABELS_FR: Dict[str, str] = {
    # Classes RDD2022
    "longitudinal_crack": "fissure longitudinale",
    "transverse_crack":   "fissure transversale",
    "alligator_crack":    "fissure en crocodile",
    "pothole":            "nid-de-poule",
    # Classes legacy urbaines
    "route_degradee":           "zone de chaussee degradee",
    "dechet":                   "accumulation de dechets",
    "eclairage_defectueux":     "point d'eclairage defectueux",
    "vegetation_envahissante":  "zone de vegetation a entretenir",
    "mobilier_casse":           "mobilier urbain endommage",
    "graffiti":                 "graffiti a nettoyer",
}

_LABELS_EN: Dict[str, str] = {
    # Classes RDD2022
    "longitudinal_crack": "longitudinal crack",
    "transverse_crack":   "transverse crack",
    "alligator_crack":    "alligator crack",
    "pothole":            "pothole",
    # Classes legacy urbaines
    "route_degradee":           "degraded road area",
    "dechet":                   "waste accumulation",
    "eclairage_defectueux":     "faulty public light",
    "vegetation_envahissante":  "overgrown vegetation",
    "mobilier_casse":           "damaged street furniture",
    "graffiti":                 "graffiti to clean",
}


class AudioGenerationService:
    """
    Service génération audio avec Bark TTS.
    Crée narration vocale du projet de réaménagement urbain.

    Supporte classes RDD2022 (longitudinal_crack, transverse_crack,
    alligator_crack, pothole) et classes legacy urbaines.
    """

    def __init__(self):
        self.models_loaded = False
        self.voice_preset  = settings.BARK_VOICE_PRESET
        self.sample_rate   = getattr(settings, "BARK_SAMPLE_RATE", SAMPLE_RATE)

    # ─────────────────────────────────────────────────────
    # Chargement modèles
    # ─────────────────────────────────────────────────────

    def load_models(self) -> None:
        """Précharge modèles Bark TTS (accélère les appels suivants)."""
        if not BARK_AVAILABLE:
            raise RuntimeError(
                "bark_not_installed: "
                "pip install git+https://github.com/suno-ai/bark.git"
            )
        try:
            print("🔊 Préchargement modèles Bark TTS...")
            preload_models()
            self.models_loaded = True
            print("✅ Modèles Bark chargés!")
        except Exception as exc:
            print(f"❌ Erreur chargement Bark: {exc}")
            raise

    # ─────────────────────────────────────────────────────
    # Génération narration principale
    # ─────────────────────────────────────────────────────

    def generate_narration(
        self,
        detection_results: Dict,
        cost_estimation: Dict,
        scenario_info: Dict,
        lang: str = "fr",
    ) -> Dict:
        """
        Génère narration audio complète du projet.

        Args:
            detection_results: Résultats détection YOLOv8
                               (supporte classes RDD2022 et legacy)
            cost_estimation:   Estimation coûts
            scenario_info:     Infos scénario choisi
            lang:              "fr" ou "en"

        Returns:
            Dict avec audio_path, duration_seconds, script, warnings
        """
        if not BARK_AVAILABLE:
            return {
                "success": False,
                "audio_path": None,
                "error": "bark_not_installed",
                "warning": "Bark TTS non disponible — installez avec pip install bark",
            }

        if not NUMPY_AVAILABLE:
            return {
                "success": False,
                "audio_path": None,
                "error": "numpy_not_installed",
                "warning": "numpy/scipy requis pour la génération audio",
            }

        if not self.models_loaded:
            try:
                self.load_models()
            except Exception as exc:
                return {
                    "success": False,
                    "audio_path": None,
                    "error": f"bark_load_failed: {exc}",
                }

        # Générer script
        script = self._create_narration_script(
            detection_results, cost_estimation, scenario_info, lang=lang
        )

        # Découper en segments
        segments = self._split_script_into_segments(script)
        audio_segments = []

        print(f"  Génération {len(segments)} segment(s) audio...")

        for i, segment in enumerate(segments):
            try:
                print(f"  Segment {i+1}/{len(segments)}...")
                audio = self._generate_segment_audio(segment)
                audio_segments.append(audio)
            except Exception as exc:
                print(f"  Erreur segment {i+1}: {exc}")

        if not audio_segments:
            return {
                "success": False,
                "audio_path": None,
                "error": "no_audio_segments_generated",
            }

        # Concaténer et sauvegarder
        full_audio = self._concatenate_audio_segments(audio_segments)
        output_path = self._save_audio(full_audio)
        duration = len(full_audio) / self.sample_rate

        return {
            "success":          True,
            "audio_path":       output_path,
            "duration_seconds": round(duration, 2),
            "sample_rate":      self.sample_rate,
            "num_segments":     len(segments),
            "script":           script,
            "format":           "wav",
            "language":         lang,
        }

    # ─────────────────────────────────────────────────────
    # Script narration
    # ─────────────────────────────────────────────────────

    def _create_narration_script(self,
        detection_results: Dict,
        cost_estimation: Dict,
        scenario_info: Dict,
        lang: str = "fr",) -> str:
        total_problems = detection_results.get("total_problems", 0)
        total_cost     = cost_estimation.get("total_cost_tnd", 0)
        scenario_type  = scenario_info.get("scenario_type", "smart")
    
        # Vision IA données
        vision = cost_estimation.get("original_image_analysis", {})
        type_espace = vision.get("type_espace", "espace urbain")
        longueur = vision.get("longueur_estimee_m", "")
        poteaux = vision.get("nb_poteaux_existants", 0)

        # Problèmes détectés
        summary = detection_results.get("summary", {})
        problems_list = [
            f"{count} {self._get_problem_label(problem, lang=lang)}"
            for problem, count in summary.items()
            if count > 0]
        problems_text = (", ".join(problems_list)
            if problems_list
            else "aucun probleme majeur detecte"
    )

        # Améliorations Vision IA
        ameliorations = cost_estimation.get("breakdown_ameliorations", [])
        amelio_list = [
            f"{a.get('description', '')} ({int(a.get('quantite', 0))} {a.get('unite', '')})"
            for a in ameliorations[:3]
    ]
        amelio_text = ", ".join(amelio_list) if amelio_list else "ameliorations urbaines"

        # Coûts par partie
        det_cost = cost_estimation.get("total_detections_tnd", 0)
        am_cost  = cost_estimation.get("total_ameliorations_tnd", 0)

        script = (
            f" Bonjour Rapport UrbanFix . "
            f"{total_problems} probleme detecte: {problems_text}. "
            f"Ameliorations proposees: {amelio_text}. "
            f"Budget total estimé: {total_cost:,.0f} dinars tunisiens. "
            f"Merci."
            )
        return script.strip()

    def _get_problem_label(self, problem_type: str, lang: str = "fr") -> str:
        """Retourne label FR/EN pour un type de problème (RDD2022 + legacy)."""
        labels = _LABELS_EN if lang == "en" else _LABELS_FR
        return labels.get(problem_type, problem_type.replace("_", " "))

    # ─────────────────────────────────────────────────────
    # Découpage segments
    # ─────────────────────────────────────────────────────

    def _split_script_into_segments(
        self, script: str, max_chars: int = 400
    ) -> List[str]:
        """
        Découpe script en segments pour Bark (~15 secondes max).
        Bark est plus stable sur des segments courts.
        """
        sentences = script.replace("\n", " ").split(". ")
        segments: List[str] = []
        current = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if not sentence.endswith("."):
                sentence += "."
            if len(current) + len(sentence) > max_chars and current:
                segments.append(current.strip())
                current = sentence + " "
            else:
                current += sentence + " "

        if current.strip():
            segments.append(current.strip())

        return segments

    # ─────────────────────────────────────────────────────
    # Génération audio
    # ─────────────────────────────────────────────────────

    def _generate_segment_audio(self, text: str):
        """Génère audio numpy pour un segment texte via Bark."""
        return generate_audio(
            text,
            history_prompt=self.voice_preset,
            text_temp=0.7,
            waveform_temp=0.7,
        )

    def _concatenate_audio_segments(self, segments: list):
        """Concatène segments audio avec silence de 0.5s entre eux."""
        silence = np.zeros(int(0.5 * self.sample_rate))
        parts = []
        for i, seg in enumerate(segments):
            parts.append(seg)
            if i < len(segments) - 1:
                parts.append(silence)
        return np.concatenate(parts)

    def _save_audio(self, audio) -> str:
        """Sauvegarde audio WAV avec nom unique (timestamp)."""
        output_dir = Path(settings.OUTPUT_DIR) / "audio"
        output_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"narration_{ts}.wav"
        output_path = output_dir / filename

        wavfile.write(str(output_path), self.sample_rate, audio)
        print(f"Audio sauvegardé: {output_path}")
        return str(output_path)

    # ─────────────────────────────────────────────────────
    # TTS simple
    # ─────────────────────────────────────────────────────

    def generate_simple_tts(self, text: str, output_name: str = "audio") -> str:
        """
        Génère audio simple depuis un texte.

        Args:
            text:        Texte à synthétiser
            output_name: Nom fichier (sans extension)

        Returns:
            Chemin fichier WAV
        """
        if not BARK_AVAILABLE:
            raise RuntimeError("bark_not_installed")
        if not NUMPY_AVAILABLE:
            raise RuntimeError("numpy_not_installed")
        if not self.models_loaded:
            self.load_models()

        audio = generate_audio(text, history_prompt=self.voice_preset)

        output_dir = Path(settings.OUTPUT_DIR) / "audio"
        output_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"{output_name}_{ts}.wav"
        wavfile.write(str(output_path), SAMPLE_RATE, audio)
        return str(output_path)


# ═══════════════════════════════════════════════════════
# Singleton + DI FastAPI
# ═══════════════════════════════════════════════════════

audio_generation_service = AudioGenerationService()


def get_audio_generation_service() -> AudioGenerationService:
    """Dependency injection FastAPI."""
    return audio_generation_service
