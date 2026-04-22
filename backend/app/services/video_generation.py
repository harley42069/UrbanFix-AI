# app/services/video_generation.py

"""
Service Génération Vidéo - Stable Video Diffusion + MoviePy
Crée vidéos transformation avant/après avec narration

Corrections v2:
- Imports avec fallback gracieux (torch, moviepy, diffusers)
- cpu_offload + vae_slicing pour RTX 4050 6GB
- Nom fichier unique (timestamp)
- TextClip safe (fallback si ImageMagick absent)
- Fallback slideshow si SVD indisponible
"""

from __future__ import annotations

import os
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# ── torch avec fallback ───────────────────────────────────────────────────────
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None  # type: ignore[assignment]
    TORCH_AVAILABLE = False

# ── numpy avec fallback ───────────────────────────────────────────────────────
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None  # type: ignore[assignment]
    NUMPY_AVAILABLE = False

# ── PIL ───────────────────────────────────────────────────────────────────────
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    Image = None  # type: ignore[assignment]
    PIL_AVAILABLE = False

# ── MoviePy avec fallback ─────────────────────────────────────────────────────
try:
    from moviepy.editor import (
        AudioFileClip,
        CompositeVideoClip,
        ImageClip,
        TextClip,
        VideoClip,
        concatenate_videoclips,
    )
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    warnings.warn("moviepy non installé. pip install moviepy")

# ── Diffusers SVD avec fallback ───────────────────────────────────────────────
try:
    from diffusers import StableVideoDiffusionPipeline
    from diffusers.utils import export_to_video, load_image
    SVD_AVAILABLE = True
except ImportError:
    StableVideoDiffusionPipeline = None  # type: ignore[assignment,misc]
    SVD_AVAILABLE = False
    warnings.warn("diffusers non installé pour SVD. pip install diffusers")

from ..core.config import settings


class VideoGenerationService:
    """
    Service génération vidéo avec Stable Video Diffusion + MoviePy.

    Fallback automatique vers slideshow simple si SVD indisponible
    (insuffisance VRAM ou modèle absent).
    """

    def __init__(self):
        self.svd_pipe = None
        self.device = (
            "cuda"
            if (TORCH_AVAILABLE and torch.cuda.is_available())
            else "cpu"
        )
        self.model_id  = getattr(settings, "SVD_MODEL_ID", "stabilityai/stable-video-diffusion-img2vid-xt")
        self.fps       = getattr(settings, "SVD_FPS", 25)
        self.num_frames = getattr(settings, "SVD_NUM_FRAMES", 14)

    # ─────────────────────────────────────────────────────
    # Chargement modèle
    # ─────────────────────────────────────────────────────

    def load_svd_model(self) -> None:
        """Charge SVD avec optimisations VRAM pour RTX 4050 6GB."""
        if not SVD_AVAILABLE:
            raise RuntimeError("svd_not_available: pip install diffusers")
        if not TORCH_AVAILABLE:
            raise RuntimeError("torch_not_installed")

        try:
            print(f"🎬 Chargement Stable Video Diffusion sur {self.device}...")
            dtype = torch.float16 if self.device == "cuda" else torch.float32

            self.svd_pipe = StableVideoDiffusionPipeline.from_pretrained(
                self.model_id,
                torch_dtype=dtype,
                variant="fp16" if self.device == "cuda" else None,
            )

            # Optimisations critiques pour 6GB VRAM
            if self.device == "cuda":
                self.svd_pipe.enable_model_cpu_offload()  # ← critique pour 6GB
                self.svd_pipe.enable_attention_slicing()
                self.svd_pipe.enable_vae_slicing()
            else:
                self.svd_pipe.to("cpu")

            print("✅ Stable Video Diffusion chargé!")

        except Exception as exc:
            print(f"❌ Erreur chargement SVD: {exc}")
            self.svd_pipe = None
            raise

    # ─────────────────────────────────────────────────────
    # Création vidéo principale
    # ─────────────────────────────────────────────────────

    def create_transformation_video(
        self,
        before_image_path: str,
        after_image_path: str,
        audio_path: Optional[str] = None,
        include_text: bool = True,
    ) -> Dict:
        """
        Crée vidéo transformation avant/après.

        Tente SVD d'abord, fallback slideshow MoviePy si SVD échoue.

        Args:
            before_image_path: Image originale (dégradée)
            after_image_path:  Image scénario (générée SDXL)
            audio_path:        Narration audio optionnelle
            include_text:      Ajouter overlays texte

        Returns:
            Dict avec video_path, duration_seconds, method utilisée
        """
        if not MOVIEPY_AVAILABLE:
            return {
                "success": False,
                "video_path": None,
                "error": "moviepy_not_installed",
                "warning": "pip install moviepy",
            }

        if not PIL_AVAILABLE:
            return {
                "success": False,
                "video_path": None,
                "error": "pillow_not_installed",
            }

        # Vérifier images source
        for path, label in [(before_image_path, "before"), (after_image_path, "after")]:
            if not Path(path).exists():
                return {
                    "success": False,
                    "video_path": None,
                    "error": f"image_not_found: {label} = {path}",
                }

        # Tenter SVD → fallback slideshow
        try:
            return self._create_svd_video(
                before_image_path, after_image_path,
                audio_path, include_text
            )
        except Exception as svd_exc:
            print(f"⚠️  SVD indisponible ({svd_exc}), fallback slideshow...")
            return self._create_slideshow_fallback(
                before_image_path, after_image_path,
                audio_path, include_text
            )

    # ─────────────────────────────────────────────────────
    # Pipeline SVD
    # ─────────────────────────────────────────────────────

    def _create_svd_video(
        self,
        before_image_path: str,
        after_image_path: str,
        audio_path: Optional[str],
        include_text: bool,
    ) -> Dict:
        """Pipeline vidéo avec Stable Video Diffusion."""
        print("🎥 Création vidéo SVD...")

        before_frames = self._generate_video_from_image(before_image_path)
        after_frames  = self._generate_video_from_image(after_image_path)

        before_clip    = self._frames_to_clip(before_frames)
        after_clip     = self._frames_to_clip(after_frames)
        transition     = self._create_transition_clip(before_image_path, after_image_path)

        clips = [before_clip, transition, after_clip]

        if include_text:
            clips = self._add_text_overlays(clips, ["ÉTAT ACTUEL", "TRANSFORMATION", "PROJET"])

        video = concatenate_videoclips(clips, method="compose")
        video = self._attach_audio(video, audio_path, after_image_path)

        output_path = self._save_video(video)
        duration = video.duration
        video.close()

        if TORCH_AVAILABLE and torch.cuda.is_available():
            torch.cuda.empty_cache()

        return {
            "success":          True,
            "video_path":       output_path,
            "duration_seconds": round(duration, 2),
            "fps":              self.fps,
            "resolution":       "1024x576",
            "has_audio":        audio_path is not None and Path(audio_path).exists(),
            "format":           "mp4",
            "method":           "svd",
        }

    def _generate_video_from_image(self, image_path: str) -> List:
        """Génère frames SVD depuis une image."""
        if self.svd_pipe is None:
            self.load_svd_model()

        image = load_image(image_path).resize((1024, 576))
        generator = torch.manual_seed(42) if TORCH_AVAILABLE else None

        print(f"  Génération {self.num_frames} frames SVD...")
        frames = self.svd_pipe(
            image,
            decode_chunk_size=4,          # ← réduit pour 6GB
            generator=generator,
            motion_bucket_id=getattr(settings, "SVD_MOTION_BUCKET_ID", 127),
            num_frames=self.num_frames,
            num_inference_steps=15,       # ← réduit pour vitesse
        ).frames[0]

        return frames

    def _frames_to_clip(self, frames: List) -> "VideoClip":
        """Convertit frames PIL en VideoClip MoviePy."""
        frame_arrays = [np.array(f) for f in frames]
        frame_duration = 1.0 / self.fps
        total_duration = len(frames) * frame_duration

        def make_frame(t: float):
            idx = min(int(t * self.fps), len(frame_arrays) - 1)
            return frame_arrays[idx]

        clip = VideoClip(make_frame, duration=total_duration)
        return clip.set_fps(self.fps)

    # ─────────────────────────────────────────────────────
    # Fallback slideshow (sans SVD)
    # ─────────────────────────────────────────────────────

    def _create_slideshow_fallback(
        self,
        before_image_path: str,
        after_image_path: str,
        audio_path: Optional[str],
        include_text: bool,
    ) -> Dict:
        """
        Fallback : slideshow simple avant → transition → après.
        Ne nécessite pas SVD, tourne sur CPU.
        """
        print("🎞️  Création slideshow fallback...")

        before_clip    = ImageClip(before_image_path).set_duration(3.0).resize((1024, 576))
        transition     = self._create_transition_clip(before_image_path, after_image_path, duration=1.5)
        after_clip     = ImageClip(after_image_path).set_duration(4.0).resize((1024, 576))

        clips = [before_clip, transition, after_clip]

        if include_text:
            clips = self._add_text_overlays(clips, ["ÉTAT ACTUEL", "TRANSFORMATION", "PROJET"])

        video = concatenate_videoclips(clips, method="compose")
        video = self._attach_audio(video, audio_path, after_image_path)

        output_path = self._save_video(video)
        duration = video.duration
        video.close()

        return {
            "success":          True,
            "video_path":       output_path,
            "duration_seconds": round(duration, 2),
            "fps":              self.fps,
            "resolution":       "1024x576",
            "has_audio":        audio_path is not None and Path(audio_path).exists(),
            "format":           "mp4",
            "method":           "slideshow_fallback",
        }

    # ─────────────────────────────────────────────────────
    # Utilitaires vidéo
    # ─────────────────────────────────────────────────────

    def _create_transition_clip(
        self,
        image1_path: str,
        image2_path: str,
        duration: float = 1.0,
    ) -> "VideoClip":
        """Crossfade entre deux images."""
        clip1 = ImageClip(image1_path).set_duration(duration).resize((1024, 576))
        clip2 = ImageClip(image2_path).set_duration(duration).resize((1024, 576))
        clip1 = clip1.crossfadeout(duration)
        clip2 = clip2.crossfadein(duration)
        return CompositeVideoClip([clip1, clip2])

    def _add_text_overlays(
        self,
        clips: List,
        titles: List[str],
    ) -> List:
        """
        Ajoute overlays texte aux clips.
        Fallback silencieux si ImageMagick absent.
        """
        overlaid = []
        for i, clip in enumerate(clips):
            if i < len(titles):
                try:
                    txt = TextClip(
                        titles[i],
                        fontsize=50,
                        color="white",
                        font="Arial-Bold",
                        stroke_color="black",
                        stroke_width=2,
                    )
                    txt = txt.set_position(("center", 50)).set_duration(clip.duration)
                    overlaid.append(CompositeVideoClip([clip, txt]))
                except Exception as exc:
                    # ImageMagick absent ou police manquante → skip texte
                    print(f"⚠️  TextClip indisponible ({exc}), overlay ignoré")
                    overlaid.append(clip)
            else:
                overlaid.append(clip)
        return overlaid

    def _attach_audio(
        self,
        video: "VideoClip",
        audio_path: Optional[str],
        last_image_path: str,
    ) -> "VideoClip":
        """Attache audio à la vidéo, prolonge si nécessaire."""
        if not audio_path or not Path(audio_path).exists():
            return video
        try:
            audio = AudioFileClip(audio_path)
            if audio.duration > video.duration:
                extra = ImageClip(last_image_path).set_duration(
                    audio.duration - video.duration
                ).resize((1024, 576))
                video = concatenate_videoclips([video, extra])
            return video.set_audio(audio)
        except Exception as exc:
            print(f"⚠️  Erreur audio: {exc}")
            return video

    def _save_video(self, video: "VideoClip") -> str:
        """Sauvegarde vidéo MP4 avec nom unique (timestamp)."""
        output_dir = Path(settings.OUTPUT_DIR) / "videos"
        output_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transformation_{ts}.mp4"
        output_path = output_dir / filename

        video.write_videofile(
            str(output_path),
            fps=self.fps,
            codec=getattr(settings, "VIDEO_OUTPUT_CODEC", "libx264"),
            audio_codec=getattr(settings, "VIDEO_OUTPUT_AUDIO_CODEC", "aac"),
            preset="medium",
            threads=4,
            logger=None,
        )

        print(f"💾 Vidéo sauvegardée: {output_path}")
        return str(output_path)

    # ─────────────────────────────────────────────────────
    # Slideshow public
    # ─────────────────────────────────────────────────────

    def create_slideshow_video(
        self,
        image_paths: List[str],
        audio_path: Optional[str] = None,
        duration_per_image: float = 3.0,
    ) -> str:
        """Crée slideshow simple depuis une liste d'images."""
        if not MOVIEPY_AVAILABLE:
            raise RuntimeError("moviepy_not_installed")

        clips = [
            ImageClip(p).set_duration(duration_per_image).resize((1024, 576))
            for p in image_paths
            if Path(p).exists()
        ]
        if not clips:
            raise ValueError("Aucune image valide fournie")

        video = concatenate_videoclips(clips, method="compose")
        video = self._attach_audio(video, audio_path, image_paths[-1])
        output_path = self._save_video(video)
        video.close()
        return output_path

    # ─────────────────────────────────────────────────────
    # Libération mémoire
    # ─────────────────────────────────────────────────────

    def unload_model(self) -> None:
        """Libère mémoire GPU."""
        if self.svd_pipe:
            del self.svd_pipe
            self.svd_pipe = None
        if TORCH_AVAILABLE and torch.cuda.is_available():
            torch.cuda.empty_cache()
        print("🗑️  Modèle SVD déchargé")


# ═══════════════════════════════════════════════════════
# Singleton + DI FastAPI
# ═══════════════════════════════════════════════════════

video_generation_service = VideoGenerationService()


def get_video_generation_service() -> VideoGenerationService:
    """Dependency injection FastAPI."""
    return video_generation_service