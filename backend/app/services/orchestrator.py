# app/services/orchestrator.py

"""
Service Orchestrateur Principal - UrbanFix AI
Corrections v5:
- Llama 4 Vision intégré dans estimate_costs (image originale + générée)
- Fix process_complete_pipeline (suppression référence variables inexistantes)
- user_prompt passé à generate_scenarios
- torch avec fallback dans get_system_status
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from ..core.config import settings
from ..schemas.scenario import (
    ScenarioAction,
    build_narration_text,
    normalize_cost_breakdown,
    normalize_scenario_type,
)
from ..utils.language import detect_language
from .storage import StorageService


class _UnavailableService:
    def __init__(self, service_name: str):
        self.service_name = service_name

    def __getattr__(self, method_name: str):
        def _raise(*_args, **_kwargs):
            raise RuntimeError(
                f"{self.service_name} unavailable: "
                f"missing optional dependency for method {method_name}"
            )
        return _raise


class OrchestratorService:
    """Orchestrateur principal pipeline UrbanFix AI."""

    def __init__(self):
        self.detection_svc = _UnavailableService("detection")
        self.image_gen_svc = _UnavailableService("image_generation")
        self.cost_svc      = _UnavailableService("cost_estimation")
        self.audio_svc     = _UnavailableService("audio_generation")
        self.video_svc     = _UnavailableService("video_generation")
        self.pdf_svc       = _UnavailableService("pdf_report")

    # ── Lazy loaders ──────────────────────────────────────────────────────────

    def _load_runtime_services(self, include_media: bool) -> None:
        self._load_detection_service()
        self._load_image_service()
        self._load_cost_service()
        if include_media:
            self._load_audio_service()
            self._load_video_service()
            self._load_pdf_service()

    @staticmethod
    def _stub_needs_runtime_load(service: object, method_name: str) -> bool:
        return isinstance(service, _UnavailableService) and method_name not in service.__dict__

    def _load_detection_service(self) -> None:
        try:
            from .detection import get_detection_service
            self.detection_svc = get_detection_service()
        except Exception:
            self.detection_svc = _UnavailableService("detection")

    def _load_image_service(self) -> None:
        try:
            from .image_generation import get_image_generation_service
            self.image_gen_svc = get_image_generation_service()
        except Exception:
            self.image_gen_svc = _UnavailableService("image_generation")

    def _load_cost_service(self) -> None:
        try:
            from .cost_estimation import get_cost_estimation_service
            self.cost_svc = get_cost_estimation_service()
        except Exception:
            self.cost_svc = _UnavailableService("cost_estimation")

    def _load_audio_service(self) -> None:
        try:
            from .audio_generation import get_audio_generation_service
            self.audio_svc = get_audio_generation_service()
        except Exception:
            self.audio_svc = _UnavailableService("audio_generation")

    def _load_video_service(self) -> None:
        try:
            from .video_generation import get_video_generation_service
            self.video_svc = get_video_generation_service()
        except Exception:
            self.video_svc = _UnavailableService("video_generation")

    def _load_pdf_service(self) -> None:
        try:
            from .pdf_report import get_pdf_report_service
            self.pdf_svc = get_pdf_report_service()
        except Exception:
            self.pdf_svc = _UnavailableService("pdf_report")

    # ── Helper ────────────────────────────────────────────────────────────────

    @staticmethod
    def _find_scenario(scenarios: list[dict], scenario_type: str) -> dict:
        for s in scenarios:
            if (
                s.get("scenario_type") == scenario_type
                or s.get("type") == scenario_type
            ):
                return s
        return scenarios[0] if scenarios else {}

    # ── Pipeline standalone ───────────────────────────────────────────────────

    def process_complete_pipeline(
        self,
        image_path: str,
        project_info: Optional[Dict] = None,
        scenario_type: str = "moderate",
        generate_all: bool = True,
    ) -> Dict:
        print("DÉMARRAGE PIPELINE URBANFIX AI")
        self._load_runtime_services(include_media=generate_all)

        start_time = datetime.now()
        results = {
            "status":       "processing",
            "image_path":   image_path,
            "project_info": project_info or {},
            "timestamp":    start_time.isoformat(),
            "steps":        {},
        }

        try:
            # Étape 1 : Détection YOLOv8
            print("\n ÉTAPE 1/6: Détection (YOLOv8)")
            detection_results = self.detection_svc.detect_problems(image_path, visualize=True)
            results["steps"]["detection"] = detection_results
            print(f" {detection_results['total_problems']} problème(s)")

            # Étape 2 : Scénarios SDXL
            print("\n ÉTAPE 2/6: Scénarios (SDXL + LoRA + Groq)")
            scenarios = self.image_gen_svc.generate_scenarios(
                detection_results,
                base_image_path=image_path,
                num_scenarios=3,
            )
            results["steps"]["scenarios"] = scenarios
            print(f"{len(scenarios)} scénarios générés")

            # Récupérer image générée pour Vision IA
            selected_scenario = self._find_scenario(scenarios, scenario_type)
            generated_image = selected_scenario.get("image_path")

            # Étape 3 : Estimation coûts avec Vision IA
            print("\n ÉTAPE 3/6: Estimation coûts (Vision + Llama)")
            region = project_info.get("location", "Tunis") if project_info else "Tunis"
            cost_estimation = self.cost_svc.estimate_costs(
                detection_results,
                scenario_type=scenario_type,
                region=region,
                image_path=image_path,
                generated_image_path=generated_image,
            )
            results["steps"]["cost_estimation"] = cost_estimation
            print(f" {cost_estimation['total_cost_tnd']:,.2f} TND")

            if not generate_all:
                results["status"]     = "success"
                results["quick_mode"] = True
                return results

            # Étape 4 : Audio Bark
            print("\n ÉTAPE 4/6: Audio (Bark TTS)")
            audio_result = self.audio_svc.generate_narration(
                detection_results, cost_estimation, selected_scenario
            )
            results["steps"]["audio"] = audio_result

            # Étape 5 : Vidéo SVD
            print("\n ÉTAPE 5/6: Vidéo (SVD)")
            after_image = selected_scenario.get("image_path", "")
            video_result: Dict = {}
            if after_image and os.path.exists(str(after_image)):
                audio_path = audio_result.get("audio_path") if audio_result.get("success") else None
                video_result = self.video_svc.create_transformation_video(
                    before_image_path=image_path,
                    after_image_path=after_image,
                    audio_path=audio_path,
                    include_text=True,
                )
                results["steps"]["video"] = video_result
            else:
                results["steps"]["video"] = {"success": False, "error": "No after image"}

            # Étape 6 : PDF
            print("\n ÉTAPE 6/6: PDF (ReportLab)")
            pdf_result = self.pdf_svc.generate_complete_report(
                project_data=project_info or {
                    "title":    "Projet réaménagement urbain",
                    "location": "Tunisie",
                    "date":     datetime.now().strftime("%d/%m/%Y"),
                },
                detection_results=detection_results,
                scenarios=scenarios,
                cost_estimation=cost_estimation,
            )
            results["steps"]["pdf_report"] = pdf_result

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            results["status"]           = "success"
            results["duration_seconds"] = round(duration, 2)
            results["completed_at"]     = end_time.isoformat()
            print(f"\n PIPELINE TERMINÉ EN {duration:.1f}s")
            return results

        except Exception as exc:
            print(f"\n ERREUR PIPELINE: {exc}")
            results["status"]       = "error"
            results["error"]        = str(exc)
            results["completed_at"] = datetime.now().isoformat()
            return results

    # ── Pipeline DB (production) ──────────────────────────────────────────────

    def process_signalement_db(
        self,
        db: "Session",
        signalement_id: int,
        user_prompt: Optional[str] = None,
        generate_media: bool = False,
        interaction_mode: str = "photo_only",
        category: str = "other",
        generate_audio: bool = False,
        generate_video: bool = False,
        generate_pdf: bool = False,
        mock_services: bool = False,
    ) -> Dict:
        """Pipeline IA complet avec persistance progressive en base de données."""
        from ..repositories.signalement_repo import (
            get_signalement,
            save_pipeline_results,
            update_signalement_status,
        )
        from ..models.signalement import SignalementStatus

        start_time = datetime.now()
        stage = "queued"
        storage = StorageService()
        scenarios_for_db: list[dict] = []

        print(f" DEBUG médias: generate_media={generate_media}, audio={generate_audio}, pdf={generate_pdf}")

        def _persist_path_or_placeholder(
            source_path: str | None,
            dest_relative_path: str,
            placeholder: bytes,
        ) -> str:
            if source_path and Path(source_path).exists():
                return storage.save_file(source_path, dest_relative_path)
            return storage.save_bytes(dest_relative_path, placeholder)

        try:
            signalement = get_signalement(db, signalement_id)
            if signalement is None:
                return {"ok": False, "error": "signalement_not_found"}

            image_path    = signalement.image_path
            prompt_source = user_prompt or f"{signalement.title}\n{signalement.description or ''}"
            lang          = detect_language(prompt_source)
            use_prompt_only = (
                interaction_mode == "prompt_only"
                or not image_path
                or str(image_path).startswith("prompt://")
            )

            metadata = dict(signalement.metadata_json or {})
            metadata.update({
                "interaction_mode": interaction_mode,
                "category":         category,
                "generate_audio":   bool(generate_audio),
                "generate_video":   bool(generate_video),
                "generate_pdf":     bool(generate_pdf),
            })
            signalement.metadata_json = metadata
            db.add(signalement)
            db.commit()

            _use_mock = mock_services or settings.ENVIRONMENT == "test"
            if _use_mock:
                from ..core.testing_fakes import (
                    FAKE_AUDIO_RESULT,
                    FAKE_COST_ESTIMATION,
                    FAKE_DETECTION_RESULT,
                    FAKE_PDF_RESULT,
                    FAKE_SCENARIOS,
                    FAKE_VIDEO_RESULT,
                )

            # ── Étape 1 : Détection ───────────────────────────────────────
            stage = "detection"
            update_signalement_status(
                db, signalement_id,
                status=SignalementStatus.PROCESSING,
                progress=5, stage=stage, last_error=None,
            )

            if use_prompt_only:
                detection_results = {
                    "total_problems":  0,
                    "detections":      [],
                    "summary":         {},
                    "annotated_image": None,
                }
            else:
                if (not _use_mock) and self._stub_needs_runtime_load(self.detection_svc, "detect_problems"):
                    self._load_detection_service()
                detection_results = (
                    FAKE_DETECTION_RESULT if _use_mock
                    else self.detection_svc.detect_problems(image_path, visualize=True)
                )

            update_signalement_status(
                db, signalement_id,
                status=SignalementStatus.PROCESSING, progress=20, stage=stage,
            )

            # ── Étape 2 : Scénarios SDXL ─────────────────────────────────
            stage = "images"
            if (not _use_mock) and self._stub_needs_runtime_load(self.image_gen_svc, "generate_scenarios"):
                self._load_image_service()
            update_signalement_status(
                db, signalement_id,
                status=SignalementStatus.PROCESSING, progress=35, stage=stage,
            )

            if use_prompt_only:
                scenarios = [
                    {
                        "id": "scn-1", "scenario_type": "basic",
                        "title":       "Basic scenario" if lang == "en" else "Scenario basique",
                        "description": "Quick low-cost rehabilitation." if lang == "en" else "Rehabilitation rapide a faible cout.",
                        "prompt_used": prompt_source, "image_path": None,
                    },
                    {
                        "id": "scn-2", "scenario_type": "smart",
                        "title":       "Smart scenario" if lang == "en" else "Scenario intelligent",
                        "description": "Balanced intervention." if lang == "en" else "Intervention equilibree.",
                        "prompt_used": prompt_source, "image_path": None,
                    },
                    {
                        "id": "scn-3", "scenario_type": "premium",
                        "title":       "Premium scenario" if lang == "en" else "Scenario premium",
                        "description": "Comprehensive transformation." if lang == "en" else "Plan de transformation complet.",
                        "prompt_used": prompt_source, "image_path": None,
                    },
                ]
            elif _use_mock:
                scenarios = list(FAKE_SCENARIOS)
            else:
                try:
                    print(f" Appel SDXL — image: {image_path}")
                    print(f"   Prompt utilisateur: {prompt_source[:80]}...")
                    scenarios = self.image_gen_svc.generate_scenarios(
                        detection_results,
                        base_image_path=image_path,
                        num_scenarios=3,
                        user_prompt=prompt_source,
                    )
                    print(f" {len(scenarios)} scénarios générés")
                    for s in scenarios:
                        print(f"   - {s.get('scenario_type')}: image={s.get('image_path')}")
                except Exception as exc:
                    import traceback
                    print(f" ERREUR generate_scenarios: {exc}")
                    traceback.print_exc()
                    scenarios = []

            scenario_items: list[dict] = []
            for _idx, scenario in enumerate(scenarios, start=1):
                stype = normalize_scenario_type(
                    scenario.get("scenario_type") or scenario.get("type")
                ).value
                scenario_url = _persist_path_or_placeholder(
                scenario.get("image_path"),
                f"{signalement_id}/scenario_{_idx}.png",
                b"fake-scenario-image",
                )
                enriched = dict(scenario)
                enriched["scenario_type"] = stype
                enriched["prompt_used"] = str(
                    scenario.get("prompt_used") or scenario.get("prompt") or prompt_source
                )
                enriched["image_url"] = scenario_url
                scenario_items.append(enriched)

            selected = scenario_items[0] if scenario_items else {}
            scenario_image_path = selected.get("image_path")
            annotated_url = None
            if not use_prompt_only:
                annotated_url = _persist_path_or_placeholder(
                    detection_results.get("annotated_image"),
                    f"process/{signalement_id}/annotated.jpg",
                    b"fake-annotated-image",
                )

            detection_payload = dict(detection_results)
            detection_payload.update({
                "annotated_image_url":  annotated_url,
                "annotated_image_path": annotated_url,
                "language":             lang,
                "interaction_mode":     interaction_mode,
                "category":             category,
            })
            update_signalement_status(
                db, signalement_id,
                status=SignalementStatus.PROCESSING, progress=60, stage=stage,
            )

           # ── Étape 3 : Estimation coûts + Vision IA ────────────────────
            stage = "cost"
            if (not _use_mock) and self._stub_needs_runtime_load(self.cost_svc, "estimate_costs"):
                self._load_cost_service()
            update_signalement_status(
                db, signalement_id,
                status=SignalementStatus.PROCESSING, progress=63, stage=stage,
            )

            region = signalement.region or "Tunis"
            cost_result = (
                FAKE_COST_ESTIMATION if _use_mock
                else self.cost_svc.estimate_costs(
                    detection_results=detection_results,
                    scenario_type="smart",
                    region=region,
                    lang=lang,
                    user_prompt=prompt_source,
                    image_path=image_path,
                    generated_image_path=scenario_image_path,
                )
            )
            cost_result = dict(cost_result)
            cost_result.update({
                "language":         lang,
                "interaction_mode": interaction_mode,
                "category":         category,
            })

            cost_breakdown_models, cost_total = normalize_cost_breakdown(cost_result)
            cost_breakdown_payload = [item.model_dump() for item in cost_breakdown_models]

            # ✅ Multiplicateurs et titres par scénario
            scenario_multipliers = {
                "basic": 1.0, "conservateur": 1.0,
                "smart": 1.5, "modere": 1.5,
                "premium": 2.5, "innovant": 2.5,
            }
            scenario_title_map_fr = {
                "basic":   "Intervention Basique (Conservatrice)",
                "smart":   "Intervention Intelligente (Recommandée)",
                "premium": "Intervention Premium (Innovante)",
            }
            scenario_title_map_en = {
                "basic":   "Basic Intervention (Conservative)",
                "smart":   "Smart Intervention (Recommended)",
                "premium": "Premium Intervention (Innovative)",
            }
            scenario_title_map = scenario_title_map_en if lang == "en" else scenario_title_map_fr

            scenarios_for_db = []
            for index, scenario in enumerate(scenario_items, start=1):
                stype = normalize_scenario_type(
                    scenario.get("scenario_type") or scenario.get("type")
                ).value
                title = str(scenario.get("title") or scenario_title_map.get(stype, stype))
                description = str(scenario.get("description") or (
                    "Targeted urban rehabilitation on degraded zones." if lang == "en"
                    else "Reamenagement urbain cible sur les zones degradees."
                ))
                actions = (
                    [
                        ScenarioAction(label="Repair road infrastructure", details="Fix degraded road segments"),
                        ScenarioAction(label="Upgrade public lighting",    details="Replace faulty light points"),
                        ScenarioAction(label="Secure pedestrian uses",     details="Improve safety and accessibility"),
                    ] if lang == "en" else [
                        ScenarioAction(label="Reparer la voirie",           details="Resorption des zones degradees"),
                        ScenarioAction(label="Mettre a niveau l'eclairage", details="Remplacement des points defectueux"),
                        ScenarioAction(label="Securiser les usages",        details="Amenagements pour usagers et pietons"),
                    ]
                )
                # ✅ Coût spécifique par scénario
                scenario_cost = round(cost_total * scenario_multipliers.get(stype, 1.5), 2)

                narration_text = build_narration_text(
                    title=title, description=description,
                    actions=actions, cost_total=scenario_cost, lang=lang,
                )
                scenarios_for_db.append({
                    "id":             str(scenario.get("id") or f"scn-{index}"),
                    "scenario_type":  stype,
                    "title":          title,
                    "description":    description,
                    "prompt_used":    str(scenario.get("prompt_used") or scenario.get("prompt") or prompt_source),
                    "image_url":      scenario.get("image_url"),
                    "image_path":     scenario.get("image_path"),
                    "narration_text": narration_text,
                    "language":       lang,
                    "actions":        [a.model_dump() for a in actions],
                    "cost_breakdown": cost_breakdown_payload,
                    "cost_total":     scenario_cost,  # ✅ coût spécifique
                })

            update_signalement_status(
                db, signalement_id,
                status=SignalementStatus.PROCESSING, progress=75, stage=stage,
            )
            save_pipeline_results(
                db, signalement_id,
                detections=detection_payload,
                scenarios=scenarios_for_db,
                estimations=cost_result,
            )

            # ── Médias facultatifs ────────────────────────────────────────
            audio_url: Optional[str] = None
            video_url: Optional[str] = None
            pdf_url:   Optional[str] = None

            if generate_media:
                legacy   = not any([generate_audio, generate_video, generate_pdf])
                do_audio = generate_audio or legacy
                do_video = generate_video or legacy
                do_pdf   = generate_pdf   or legacy

                if do_audio:
                    stage = "audio"
                    if (not _use_mock) and self._stub_needs_runtime_load(self.audio_svc, "generate_narration"):
                        self._load_audio_service()
                    update_signalement_status(
                        db, signalement_id,
                        status=SignalementStatus.PROCESSING, progress=78, stage=stage,
                    )
                    narration_scenario = (
                        scenarios_for_db[1] if len(scenarios_for_db) > 1
                        else (scenarios_for_db[0] if scenarios_for_db else selected)
                    )
                    audio_result = (
                        {**FAKE_AUDIO_RESULT, "script": narration_scenario.get("narration_text", "")}
                        if _use_mock
                        else self.audio_svc.generate_narration(
                            detection_results, cost_result, narration_scenario, lang=lang
                        )
                    )
                    if audio_result.get("success"):
                        audio_url = _persist_path_or_placeholder(
                            audio_result.get("audio_path"),
                            f"{signalement_id}/narration.mp3",
                            b"fake-audio",
                        )
                    update_signalement_status(
                        db, signalement_id,
                        status=SignalementStatus.PROCESSING, progress=85, stage=stage,
                    )

                if do_video:
                    stage = "video"
                    if (not _use_mock) and self._stub_needs_runtime_load(self.video_svc, "create_transformation_video"):
                        self._load_video_service()
                    update_signalement_status(
                        db, signalement_id,
                        status=SignalementStatus.PROCESSING, progress=88, stage=stage,
                    )
                    if _use_mock:
                        video_url = _persist_path_or_placeholder(
                            FAKE_VIDEO_RESULT.get("video_path"),
                            f"{signalement_id}/transformation.mp4",
                            b"fake-video",
                        )
                    elif scenario_image_path and os.path.exists(str(scenario_image_path)):
                        video_result = self.video_svc.create_transformation_video(
                            before_image_path=image_path,
                            after_image_path=scenario_image_path,
                            audio_path=audio_url,
                            include_text=True,
                        )
                        if video_result.get("success"):
                            video_url = _persist_path_or_placeholder(
                                video_result.get("video_path"),
                                f"{signalement_id}/transformation.mp4",
                                b"fake-video",
                            )
                    update_signalement_status(
                        db, signalement_id,
                        status=SignalementStatus.PROCESSING, progress=95, stage=stage,
                    )

                if do_pdf:
                    stage = "pdf"
                    if (not _use_mock) and self._stub_needs_runtime_load(self.pdf_svc, "generate_complete_report"):
                        self._load_pdf_service()
                    update_signalement_status(
                        db, signalement_id,
                        status=SignalementStatus.PROCESSING, progress=97, stage=stage,
                    )
                    pdf_result = (
                        FAKE_PDF_RESULT if _use_mock
                        else self.pdf_svc.generate_complete_report(
                            project_data={
                                "title":    signalement.title,
                                "location": signalement.city,
                                "date":     datetime.now().strftime("%d/%m/%Y"),
                            },
                            detection_results=detection_results,
                            scenarios=scenarios_for_db,
                            cost_estimation=cost_result,
                            lang=lang,
                        )
                    )
                    if pdf_result.get("success"):
                        pdf_url = _persist_path_or_placeholder(
                            pdf_result.get("pdf_path"),
                            f"{signalement_id}/report.pdf",
                            b"%PDF-1.4\nfake-report\n",
                        )

            # ── Finalisation ──────────────────────────────────────────────
            processing_time = (datetime.now() - start_time).total_seconds()
            save_pipeline_results(
                db, signalement_id,
                audio_url=audio_url,
                video_url=video_url,
                pdf_url=pdf_url,
                processing_time=processing_time,
            )
            update_signalement_status(
                db, signalement_id,
                status=SignalementStatus.COMPLETED,
                progress=100, stage="completed", last_error=None,
            )
            print(f"process_signalement_db terminé en {processing_time:.1f}s")
            return {
                "ok":                      True,
                "signalement_id":          signalement_id,
                "processing_time_seconds": round(processing_time, 2),
            }

        except Exception as exc:
            from ..repositories.signalement_repo import update_signalement_status
            from ..models.signalement import SignalementStatus
            try:
                update_signalement_status(
                    db, signalement_id,
                    status=SignalementStatus.FAILED,
                    progress=0, stage="failed",
                    last_error={"stage": stage, "message": str(exc)},
                )
            except Exception:
                pass
            print(f"process_signalement_db erreur [{stage}]: {exc}")
            return {"ok": False, "error": str(exc), "stage": stage}

    # ── Utilitaires ───────────────────────────────────────────────────────────

    def process_quick_analysis(self, image_path: str) -> Dict:
        print("Mode analyse rapide")
        return self.process_complete_pipeline(image_path, generate_all=False)

    def unload_all_models(self) -> None:
        print(" Déchargement modèles IA...")
        for svc, method in [
            (self.image_gen_svc, "unload_model"),
            (self.video_svc,     "unload_model"),
        ]:
            try:
                if not isinstance(svc, _UnavailableService):
                    getattr(svc, method)()
            except Exception:
                pass
        print("Modèles déchargés")

    def get_system_status(self) -> Dict:
        cuda_available = False
        cuda_device    = None
        try:
            import torch
            cuda_available = torch.cuda.is_available()
            cuda_device    = torch.cuda.get_device_name(0) if cuda_available else None
        except ImportError:
            pass

        return {
            "services": {
                "detection":        "ready" if not isinstance(self.detection_svc, _UnavailableService) else "unavailable",
                "image_generation": "ready" if not isinstance(self.image_gen_svc, _UnavailableService) else "unavailable",
                "cost_estimation":  "ready" if not isinstance(self.cost_svc,      _UnavailableService) else "unavailable",
                "audio_generation": "ready" if not isinstance(self.audio_svc,     _UnavailableService) else "unavailable",
                "video_generation": "ready" if not isinstance(self.video_svc,     _UnavailableService) else "unavailable",
                "pdf_report":       "ready" if not isinstance(self.pdf_svc,       _UnavailableService) else "unavailable",
            },
            "system": {
                "cuda_available": cuda_available,
                "cuda_device":    cuda_device,
                "models_dir":     settings.MODELS_DIR,
                "output_dir":     settings.OUTPUT_DIR,
            },
            "config": {
                "yolo_model":        settings.YOLO_MODEL_PATH,
                "sdxl_model":        settings.SDXL_MODEL_ID,
                "groq_configured":   bool(settings.GROQ_API_KEY),
                "detection_classes": settings.DETECTION_CLASSES,
            },
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

orchestrator_service = OrchestratorService()


def get_orchestrator_service() -> OrchestratorService:
    return orchestrator_service