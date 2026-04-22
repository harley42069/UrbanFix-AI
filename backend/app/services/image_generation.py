"""Service SDXL + LoRA for UrbanFix scenario image generation.

Corrections v3:
- _strength défini DANS la boucle for (pas en dehors de la classe)
- strength adapté par scénario: conservateur=0.30, modere=0.50, innovant=0.70
- Groq enrichit le prompt avec "same street structure preserved"
- Meilleure gestion des erreurs avec traceback complet
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
import traceback
from pathlib import Path
from typing import Any

from PIL import Image

try:
    import torch
except Exception as exc:
    torch = None  # type: ignore[assignment]
    _TORCH_IMPORT_ERROR: Exception | None = exc
else:
    _TORCH_IMPORT_ERROR = None

try:
    from diffusers import StableDiffusionXLImg2ImgPipeline, StableDiffusionXLPipeline
except Exception as exc:
    StableDiffusionXLPipeline = None  # type: ignore[assignment]
    StableDiffusionXLImg2ImgPipeline = None  # type: ignore[assignment]
    _DIFFUSERS_IMPORT_ERROR: Exception | None = exc
else:
    _DIFFUSERS_IMPORT_ERROR = None

from ..core.config import settings
from ..core.files import write_image_safe


def _safe_print(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        print(message.encode("ascii", "replace").decode("ascii"))


# ─────────────────────────────────────────────────────────────────────────────
# Groq prompt enrichment
# ─────────────────────────────────────────────────────────────────────────────

def _enrich_prompt_with_groq(user_prompt: str, scenario_type: str) -> str | None:
    """Utilise Groq/Llama pour enrichir le prompt utilisateur en prompt SDXL optimisé."""
    if not getattr(settings, "GROQ_API_KEY", None):
        return None

    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)

        scenario_descriptions = {
            "conservateur": "réparations minimales : nettoyer, repeindre, reboucher les fissures",
            "modere":       "transformation modérée : végétation, éclairage LED, mobilier urbain rénové",
            "innovant":     "transformation premium : architecture tunisienne restaurée, jardin luxuriant, fontaine, pavés traditionnels",
        }
        scenario_desc = scenario_descriptions.get(scenario_type, "rénovation urbaine")

        system_prompt = system_prompt = """Tu es un expert en visualisation de réaménagement urbain avec Stable Diffusion XL.
Tu génères des prompts SDXL pour visualiser des améliorations urbaines RÉALISTES.

RÈGLES ABSOLUES — NE JAMAIS VIOLER:
- Commence TOUJOURS par "tnrenovation"
- TOUJOURS inclure: "same road width, same perspective, same existing trees, same building facades, no new construction, no added people, no new buildings"
- INTERDITS ABSOLUS: nouveaux bâtiments, nouvelles maisons, nouvelles personnes, changer la géométrie de la rue, ajouter des structures inexistantes
- Termine TOUJOURS par "photorealistic, hyperrealistic, 8k, urban renovation visualization"
- Maximum 90 mots
- Réponds UNIQUEMENT avec le prompt, rien d'autre

AUTORISÉ UNIQUEMENT:
 Réparer/lisser la surface de la route existante
 Ajouter de la végétation UNIQUEMENT dans les espaces verts existants
 Changer la couleur/peinture des murs existants
 Ajouter lampadaires sur poteaux existants ou dans espaces libres sur les bords
 Marquage routier neuf sur la route existante
 Mobilier urbain (bancs, poubelles) dans espaces libres existants
 Nettoyer, réparer trottoirs existants

NIVEAUX DE TRANSFORMATION:
- conservateur: smooth repaired road surface + fresh road markings + clean surroundings, minimal changes
- modere: smooth road + solar streetlights on road edges + vegetation in existing green spaces + fresh markings
- innovant: smooth road + solar LED streetlights + bike lane on existing road + lush vegetation in existing spaces + premium road markings + clean urban furniture in free spaces

CONTEXTES SUPPORTÉS:
- Route fissurée → lisser asphalte, corriger marquage
- Rue étroite médina → repeindre murs, plantes sur rebords
- Boulevard → trottoirs, végétation, éclairage
- Banlieue → organiser espaces, végétation, signalisation"""

        user_message = f"""Type d'espace urbain et problèmes détectés: {user_prompt}
Niveau de transformation demandé: {scenario_desc}

Génère un prompt SDXL strict qui respecte EXACTEMENT la géométrie existante."""

        response = client.chat.completions.create(
            model=getattr(settings, "GROQ_MODEL_ID", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            temperature=0.7,
            max_tokens=60,
        )

        enriched = response.choices[0].message.content.strip()
        _safe_print(f"[Groq] Prompt enrichi ({scenario_type}): {enriched[:80]}...")
        return enriched

    except Exception as exc:
        _safe_print(f"[Groq] Enrichissement indisponible: {exc}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Service
# ─────────────────────────────────────────────────────────────────────────────

class ImageGenerationService:
    """Generate 3 urban renovation scenarios using SDXL + LoRA."""

    _load_lock: threading.Lock = threading.Lock()
    _txt2img_pipe: Any = None
    _img2img_pipe: Any = None
    _load_error: str | None = None
    _is_loaded: bool = False

    # Strength par scénario — défini comme attribut de classe
    STRENGTH_MAP: dict[str, float] = {
        "conservateur": 0.25,  # garde 70% de l'image originale
        "modere":       0.4,  # transformation équilibrée
        "innovant":     0.55,  # transformation maximale
    }

    def __init__(self) -> None:
        self.device = "cuda" if (torch is not None and torch.cuda.is_available()) else "cpu"
        self.output_dir = Path(settings.OUTPUT_DIR) / "scenarios"
        self.base_model = os.getenv("SDXL_BASE_MODEL") or getattr(
            settings, "SDXL_MODEL_ID", "stabilityai/stable-diffusion-xl-base-1.0",
        )
        self.lora_model_path = os.getenv("LORA_MODEL_PATH") or getattr(
            settings, "SDXL_LORA_PATH", "./models/tnrenovation_lora.safetensors",
        )
        self.trigger_token = os.getenv("LORA_TRIGGER_TOKEN", "tnrenovation")
        self.num_inference_steps = int(os.getenv(
            "SDXL_NUM_INFERENCE_STEPS",
            str(getattr(settings, "SDXL_NUM_INFERENCE_STEPS", 25)),
        ))
        self.guidance_scale = float(os.getenv(
            "SDXL_GUIDANCE_SCALE",
            str(getattr(settings, "SDXL_GUIDANCE_SCALE", 7.5)),
        ))
        self.negative_prompt = (
        "new buildings, added people, changed road structure, "
        "different architecture, blurry, low quality, watermark, "
        "ugly, deformed, unrealistic, cartoon, painting, drawing, "
        "extra buildings, demolished walls, different perspective, "
        "new construction, crowded, busy street")
        self.default_scenario_types = ["conservateur", "modere", "innovant"]

    @property
    def pipe(self) -> Any:
        return ImageGenerationService._txt2img_pipe

    @staticmethod
    def _normalize_scenario_type(value: str) -> str:
        key = (value or "modere").strip().lower()
        if key in {"conservateur", "conservative", "minimal", "basic"}:
            return "conservateur"
        if key in {"modere", "moderate", "smart"}:
            return "modere"
        if key in {"innovant", "innovative", "premium"}:
            return "innovant"
        return "modere"

    def _prompt_for(self, scenario_type: str, user_prompt: str | None = None) -> str:
        """Construit le prompt SDXL — enrichi par Groq si user_prompt fourni."""
        normalized = self._normalize_scenario_type(scenario_type)
        token = self.trigger_token

        if user_prompt and user_prompt.strip():
            enriched = _enrich_prompt_with_groq(user_prompt.strip(), normalized)
            if enriched:
                return enriched

        prompts = {
            "conservateur": (
                f"{token}, repaired tunisian street, same street structure preserved, "
                "keep existing buildings, clean sidewalk, fresh paint, "
                "warm mediterranean sunlight, photorealistic, 8k"
            ),
            "modere": (
                f"{token}, renovated tunisian urban space, same street structure preserved, "
                "keep existing buildings, modern lighting, green trees, "
                "clean road, photorealistic, 8k"
            ),
            "innovant": (
                f"{token}, smart tunisian city street, same street structure preserved, "
                "keep existing buildings, solar LED lights, bike lane, "
                "vertical garden, premium urban furniture, photorealistic, 8k"
            ),
        }
        return prompts[normalized]

    @staticmethod
    def _legacy_type_for(scenario_type: str) -> str:
        normalized = ImageGenerationService._normalize_scenario_type(scenario_type)
        return {"conservateur": "basic", "modere": "smart", "innovant": "premium"}[normalized]

    def _fallback_result(self, scenario_type: str, warning: str) -> dict[str, Any]:
        prompt = self._prompt_for(scenario_type)
        normalized = self._normalize_scenario_type(scenario_type)
        return {
            "scenario_type":           normalized,
            "type":                    self._legacy_type_for(normalized),
            "image_path":              None,
            "prompt_used":             prompt,
            "prompt":                  prompt,
            "generation_time_seconds": 0.0,
            "warning":                 warning,
        }

    @staticmethod
    def _release_vram() -> None:
        if torch is not None and torch.cuda.is_available():
            torch.cuda.empty_cache()

    def _enable_low_vram_optimizations(self, pipe: Any) -> None:
        try:
            if self.device == "cuda":
                pipe.enable_model_cpu_offload()
                pipe.enable_attention_slicing()
            else:
                pipe.to("cpu")
                pipe.enable_attention_slicing()
        except Exception as e:
            _safe_print(f"[ImageGeneration] VRAM optim warning: {e}")

    def _ensure_model_loaded(self) -> tuple[bool, str | None]:
        """Lazy-load SDXL pipelines + LoRA only once."""
        if ImageGenerationService._is_loaded:
            return True, None
        if ImageGenerationService._load_error:
            return False, ImageGenerationService._load_error

        if _DIFFUSERS_IMPORT_ERROR is not None:
            msg = f"diffusers_not_installed: {_DIFFUSERS_IMPORT_ERROR}"
            ImageGenerationService._load_error = msg
            return False, msg

        if _TORCH_IMPORT_ERROR is not None:
            msg = f"torch_not_installed: {_TORCH_IMPORT_ERROR}"
            ImageGenerationService._load_error = msg
            return False, msg

        if not self.lora_model_path or not Path(self.lora_model_path).exists():
            msg = f"lora_model_missing: {self.lora_model_path}"
            ImageGenerationService._load_error = msg
            return False, msg

        with ImageGenerationService._load_lock:
            if ImageGenerationService._is_loaded:
                return True, None
            if ImageGenerationService._load_error:
                return False, ImageGenerationService._load_error

            try:
                _safe_print(f"[ImageGeneration] Loading SDXL base model on {self.device}...")
                dtype = torch.float16 if self.device == "cuda" else torch.float32

                txt2img = StableDiffusionXLPipeline.from_pretrained(
                    self.base_model,
                    torch_dtype=dtype,
                    use_safetensors=True,
                    variant="fp16" if self.device == "cuda" else None,
                )

                _safe_print(f"[ImageGeneration] Loading LoRA: {self.lora_model_path}")
                txt2img.load_lora_weights(self.lora_model_path)

                # cpu_offload AVANT création img2img pipe
                self._enable_low_vram_optimizations(txt2img)

                img2img = StableDiffusionXLImg2ImgPipeline(**txt2img.components)
                self._enable_low_vram_optimizations(img2img)

                ImageGenerationService._txt2img_pipe = txt2img
                ImageGenerationService._img2img_pipe = img2img
                ImageGenerationService._is_loaded = True
                _safe_print("[ImageGeneration] SDXL + LoRA loaded successfully.")
                return True, None

            except Exception as exc:
                msg = f"sdxl_load_failed: {exc}"
                _safe_print(f"[ImageGeneration] Load failed: {traceback.format_exc()}")
                ImageGenerationService._load_error = msg
                self._release_vram()
                return False, msg

    def generate_scenarios(
        self,
        detection_results: dict,
        source_image_path: str | None = None,
        scenario_types: list[str] = ["conservateur", "modere", "innovant"],
        user_prompt: str | None = None,
        **kwargs: Any,
    ) -> list[dict]:
        """
        Génère 3 scénarios SDXL avec enrichissement Groq automatique.

        Args:
            detection_results: Résultats YOLOv8 (réservé futur usage)
            source_image_path: Image source pour img2img
            scenario_types:    Types de scénarios à générer
            user_prompt:       Prompt utilisateur → enrichi par Groq/Llama
        """
        del detection_results  # Réservé pour futur prompt-conditioning

        if source_image_path is None:
            source_image_path = kwargs.get("base_image_path")

        normalized = [
            self._normalize_scenario_type(s)
            for s in (scenario_types or self.default_scenario_types)
        ]

        num_scenarios = kwargs.get("num_scenarios")
        if isinstance(num_scenarios, int) and num_scenarios > 0:
            normalized = normalized[:num_scenarios]
        if not normalized:
            normalized = list(self.default_scenario_types)

        ok, warning = self._ensure_model_loaded()
        if not ok:
            _safe_print(f"[ImageGeneration] Modèle indisponible: {warning}")
            return [self._fallback_result(s, warning or "image_generation_unavailable") for s in normalized]

        output_dir = self.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Charger image source pour img2img
        init_image: Image.Image | None = None
        if source_image_path:
            src = Path(source_image_path)
            if not src.exists():
                _safe_print(f"[ImageGeneration] Image source introuvable: {source_image_path}")
                return [self._fallback_result(s, f"source_image_not_found: {source_image_path}") for s in normalized]
            try:
                with Image.open(src) as img:
                    init_image = img.convert("RGB").resize((768, 768), Image.Resampling.LANCZOS)
                _safe_print(f"[ImageGeneration] Image source chargée: {src.name} → img2img mode")
            except Exception as exc:
                _safe_print(f"[ImageGeneration] Erreur chargement image: {exc}")
                return [self._fallback_result(s, f"source_image_load_failed: {exc}") for s in normalized]

        results: list[dict[str, Any]] = []

        for idx, scenario_type in enumerate(normalized):

            # _strength défini ICI dans la boucle
            _strength = self.STRENGTH_MAP.get(scenario_type, 0.50)

            # Prompt enrichi par Groq
            prompt = self._prompt_for(scenario_type, user_prompt=user_prompt)
            _safe_print(f"[ImageGeneration] Génération {scenario_type} ({idx+1}/{len(normalized)})...")
            _safe_print(f"   Prompt: {prompt[:100]}...")
            _safe_print(f"   Strength: {_strength}")

            start = time.perf_counter()
            try:
                if init_image is not None:
                    _safe_print(f"   Mode: img2img (strength={_strength})")
                    output = ImageGenerationService._img2img_pipe(
                        prompt=prompt,
                        negative_prompt=self.negative_prompt,
                        image=init_image,
                        strength=_strength,          # ✅ strength adapté par scénario
                        num_inference_steps=self.num_inference_steps,
                        guidance_scale=self.guidance_scale,
                    )
                else:
                    _safe_print("   Mode: txt2img")
                    output = ImageGenerationService._txt2img_pipe(
                        prompt=prompt,
                        negative_prompt=self.negative_prompt,
                        height=768,
                        width=768,
                        num_inference_steps=self.num_inference_steps,
                        guidance_scale=self.guidance_scale,
                    )

                image = output.images[0].convert("RGB")
                filename = f"scenario_{idx + 1}.jpg"
                output_path = output_dir / filename
                write_image_safe(image, output_path, format="JPEG", quality=95)

                elapsed = round(time.perf_counter() - start, 3)
                _safe_print(f"  Image sauvegardée: {output_path} ({elapsed}s)")

                results.append({
                    "scenario_type":           scenario_type,
                    "type":                    self._legacy_type_for(scenario_type),
                    "image_path":              str(output_path),
                    "prompt_used":             prompt,
                    "prompt":                  prompt,
                    "generation_time_seconds": elapsed,
                    "strength_used":           _strength,
                })

            except Exception as exc:
                elapsed = round(time.perf_counter() - start, 3)
                _safe_print(f"  Erreur génération {scenario_type}: {exc}")
                _safe_print(traceback.format_exc())
                results.append({
                    "scenario_type":           scenario_type,
                    "type":                    self._legacy_type_for(scenario_type),
                    "image_path":              None,
                    "prompt_used":             prompt,
                    "prompt":                  prompt,
                    "generation_time_seconds": elapsed,
                    "warning":                 f"generation_failed: {exc}",
                })
            finally:
                self._release_vram()

        return results

    def unload_model(self) -> None:
        """Unload singleton pipelines and clear VRAM."""
        with ImageGenerationService._load_lock:
            ImageGenerationService._txt2img_pipe = None
            ImageGenerationService._img2img_pipe = None
            ImageGenerationService._is_loaded = False
            ImageGenerationService._load_error = None
        self._release_vram()
        _safe_print("[ImageGeneration] SDXL pipelines unloaded.")


# ─────────────────────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────────────────────

image_generation_service = ImageGenerationService()


def get_image_generation_service() -> ImageGenerationService:
    """Return singleton image generation service."""
    return image_generation_service


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone SDXL + LoRA scenario generation test")
    parser.add_argument("--source_image_path", type=str, default=None)
    parser.add_argument("--user_prompt", type=str, default=None)
    parser.add_argument("--scenario_types", type=str, default="conservateur,modere,innovant")
    args = parser.parse_args()

    scenario_types = [s.strip() for s in args.scenario_types.split(",") if s.strip()]
    svc = ImageGenerationService()
    payload = svc.generate_scenarios(
        detection_results={},
        source_image_path=args.source_image_path,
        scenario_types=scenario_types,
        user_prompt=args.user_prompt,
    )
    try:
        _safe_print(json.dumps(payload, ensure_ascii=False, indent=2))
    except Exception:
        _safe_print(str(payload))