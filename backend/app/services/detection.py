"""
Service Détection IA - YOLOv8 (best.pt RDD2022)
Détecte 4 types de dommages routiers:
    longitudinal_crack | transverse_crack | alligator_crack | pothole
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import cv2
except Exception:
    cv2 = None

try:
    import numpy as np
except Exception:
    np = None

YOLO = None
_YOLO_IMPORT_ERROR: Exception | None = None

try:
    from PIL import Image
except Exception:
    Image = None

from ..core.config import settings
from ..schemas.detection import DetectionBox, DetectionResult


logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════
# Classes RDD2022 — alignées avec best.pt entraîné
# ═══════════════════════════════════════════════════════

RDD2022_CLASSES: Dict[int, str] = {
    0: "longitudinal_crack",
    1: "transverse_crack",
    2: "alligator_crack",
    3: "pothole",
}

# Couleurs BGR par classe (pour annotations OpenCV)
RDD2022_COLORS: Dict[str, Tuple[int, int, int]] = {
    "longitudinal_crack": (0, 165, 255),   # Orange
    "transverse_crack":   (0, 255, 255),   # Jaune
    "alligator_crack":    (0, 0, 255),     # Rouge
    "pothole":            (255, 0, 0),     # Bleu
}

# Labels affichés dans les annotations
RDD2022_LABELS: Dict[str, str] = {
    "longitudinal_crack": "Fissure longitudinale",
    "transverse_crack":   "Fissure transversale",
    "alligator_crack":    "Fissure en crocodile",
    "pothole":            "Nid-de-poule",
}


class DetectionService:
    """
    Service détection dommages routiers avec YOLOv8 (best.pt RDD2022).

    Classes détectées:
        - longitudinal_crack  (mAP50: 0.532)
        - transverse_crack    (mAP50: 0.513)
        - alligator_crack     (mAP50: 0.607)
        - pothole             (mAP50: 0.713)
    """

    def __init__(self):
        self.model = None
        self.model_path: str = settings.YOLO_MODEL_PATH
        self.confidence_threshold: float = settings.YOLO_CONFIDENCE_THRESHOLD
        self.iou_threshold: float = settings.YOLO_IOU_THRESHOLD
        self._missing_model_warning_logged = False
        # Classes figées sur RDD2022 — ne pas lire depuis settings
        self.classes: Dict[int, str] = RDD2022_CLASSES
        self._warn_if_model_missing()

    def _warn_if_model_missing(self) -> None:
        """Log once when YOLO model file is missing on configured stable path."""
        if self._missing_model_warning_logged:
            return
        model_file = Path(self.model_path)
        if model_file.exists():
            return

        logger.warning(
            "YOLO model not found at %s. Expected stable model path is "
            "backend/models/yolo_road_damage_best.pt (or ./models/yolo_road_damage_best.pt "
            "from backend cwd). Detection will run in fallback mode.",
            str(model_file),
        )
        self._missing_model_warning_logged = True

    # ─────────────────────────────────────────────────────
    # Chargement modèle
    # ─────────────────────────────────────────────────────

    def load_model(self) -> None:
        """
        Charge best.pt depuis settings.YOLO_MODEL_PATH.
        Lève RuntimeError si le fichier est absent ou si
        ultralytics n'est pas installé.
        """
        global YOLO, _YOLO_IMPORT_ERROR

        # Import ultralytics une seule fois
        if YOLO is None:
            if _YOLO_IMPORT_ERROR is not None:
                raise RuntimeError("ultralytics_not_installed")
            try:
                from ultralytics import YOLO as _YOLO
                YOLO = _YOLO
            except Exception as exc:
                _YOLO_IMPORT_ERROR = exc
                raise RuntimeError("ultralytics_not_installed")

        model_file = Path(self.model_path)

        if not model_file.exists():
            raise FileNotFoundError(str(model_file))

        print(f" Chargement best.pt → {self.model_path}")
        self.model = YOLO(str(model_file))

        # Vérifier que le modèle a bien 4 classes RDD2022
        if hasattr(self.model, "names"):
            loaded_names = self.model.names
            expected = set(RDD2022_CLASSES.values())
            loaded = set(loaded_names.values()) if isinstance(loaded_names, dict) else set(loaded_names)
            if not expected.issubset(loaded):
                print(
                    f" Classes modèle: {loaded}\n"
                    f"   Classes attendues: {expected}\n"
                    "   Vérifie que best.pt est bien le modèle RDD2022."
                )
            else:
                # Utiliser le mapping exact du modèle chargé
                if isinstance(loaded_names, dict):
                    self.classes = loaded_names
                print(f" Modèle chargé — classes: {list(self.classes.values())}")

    # ─────────────────────────────────────────────────────
    # Détection principale
    # ─────────────────────────────────────────────────────

    def detect_problems(
        self,
        image_path: str,
        confidence: Optional[float] = None,
        confidence_threshold: Optional[float] = None,
        visualize: bool = True,
        process_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Détecte dommages routiers dans une image avec best.pt.

        Args:
            image_path:           Chemin vers l'image à analyser.
            confidence:           Seuil confiance (priorité 1).
            confidence_threshold: Seuil confiance (priorité 2, alias).
            visualize:            Générer l'image annotée.

        Returns:
            Dict avec clés:
                detections        – liste legacy (compatible pipeline)
                summary           – {class_name: count}
                statistics        – coverage, density, avg_confidence
                annotated_image   – chemin image annotée ou None
                total_problems    – int
                confidence_threshold – float utilisé
                model_name        – "yolov8"
                model_version     – nom du fichier best.pt
                boxes             – liste DetectionBox sérialisée
                warnings          – liste avertissements
        """
        conf_threshold = (
            confidence
            if confidence is not None
            else (
                confidence_threshold
                if confidence_threshold is not None
                else self.confidence_threshold
            )
        )

        warnings: List[str] = []
        image_width = image_height = 0
        image = None

        input_path = Path(image_path)

        # Fallback gracieux: chemin image invalide.
        if not input_path.exists():
            warnings.append(f"image_not_found: {image_path}")
            result_model = DetectionResult(
                model_name="yolov8",
                model_version=Path(self.model_path).name,
                image_width=0,
                image_height=0,
                boxes=[],
                warnings=warnings,
            )
            payload = result_model.model_dump()
            payload["detections"] = []
            payload["summary"] = self._generate_summary([])
            payload["statistics"] = self._calculate_statistics([], (1, 1, 3))
            payload["annotated_image"] = None
            payload["total_problems"] = 0
            payload["confidence_threshold"] = conf_threshold
            return payload

        # Lire dimensions image
        if cv2 is not None:
            image = cv2.imread(image_path)
            if image is not None:
                image_height, image_width = image.shape[:2]
        
        if (image_width == 0 or image_height == 0) and Image is not None:
            with Image.open(image_path) as pil_img:
                image_width, image_height = pil_img.size

        if image_width == 0 or image_height == 0:
            warnings.append(f"image_not_found: {image_path}")
            result_model = DetectionResult(
                model_name="yolov8",
                model_version=Path(self.model_path).name,
                image_width=0,
                image_height=0,
                boxes=[],
                warnings=warnings,
            )
            payload = result_model.model_dump()
            payload["detections"] = []
            payload["summary"] = self._generate_summary([])
            payload["statistics"] = self._calculate_statistics([], (1, 1, 3))
            payload["annotated_image"] = None
            payload["total_problems"] = 0
            payload["confidence_threshold"] = conf_threshold
            return payload

        boxes: List[DetectionBox] = []
        annotated_image_path: Optional[str] = None

        try:
            self._warn_if_model_missing()
            if self.model is None:
                self.load_model()

            results = self.model.predict(
                source=image_path,
                conf=conf_threshold,
                iou=self.iou_threshold,
                verbose=False,
            )

            boxes = self._parse_detections(results[0])

            if visualize and image is not None and cv2 is not None:
                annotated_image_path = self._create_annotated_image(
                    image, boxes, image_path, process_id=process_id
                )

        except Exception as exc:
            if isinstance(exc, FileNotFoundError):
                warnings.append(f"yolo_model_not_found: {self.model_path}")
            elif isinstance(exc, RuntimeError) and "ultralytics_not_installed" in str(exc):
                warnings.append("ultralytics_not_installed")
            else:
                warnings.append(f"detection unavailable: {exc}")

        # Construire DetectionResult (schéma Pydantic)
        result_model = DetectionResult(
            model_name="yolov8",
            model_version=Path(self.model_path).name,
            image_width=image_width,
            image_height=image_height,
            boxes=boxes,
            warnings=warnings,
        )

        payload = result_model.model_dump()

        # Couche de compatibilité legacy (pipeline / frontend)
        legacy_detections = self._to_legacy_detections(boxes)
        payload["detections"]          = legacy_detections
        payload["summary"]             = self._generate_summary(boxes)
        payload["statistics"]          = self._calculate_statistics(
            legacy_detections, (image_height, image_width, 3)
        )
        payload["annotated_image"]     = annotated_image_path
        payload["annotated_image_path"] = annotated_image_path
        payload["total_problems"]      = len(legacy_detections)
        payload["confidence_threshold"] = conf_threshold

        return payload

    # ─────────────────────────────────────────────────────
    # Parsing résultats YOLO
    # ─────────────────────────────────────────────────────

    def _parse_detections(self, result) -> List[DetectionBox]:
        """Parse un objet Results YOLOv8 en liste DetectionBox."""
        detections: List[DetectionBox] = []

        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            class_id   = int(box.cls[0].cpu().numpy())
            confidence = float(box.conf[0].cpu().numpy())
            class_name = self._get_class_name(class_id)

            detections.append(
                DetectionBox(
                    x1=int(x1),
                    y1=int(y1),
                    x2=int(x2),
                    y2=int(y2),
                    conf=round(confidence, 3),
                    class_id=class_id,
                    class_name=class_name,
                )
            )

        return detections

    def _get_class_name(self, class_id: int) -> str:
        """
        Mappe class_id → nom RDD2022.
        Utilise self.classes (mis à jour depuis best.pt au chargement).
        """
        if class_id in self.classes:
            return self.classes[class_id]
        # Fallback sur le dict statique
        if class_id in RDD2022_CLASSES:
            return RDD2022_CLASSES[class_id]
        return f"unknown_{class_id}"

    # ─────────────────────────────────────────────────────
    # Résumé & statistiques
    # ─────────────────────────────────────────────────────

    def _generate_summary(self, boxes: List[DetectionBox]) -> Dict[str, int]:
        """Retourne {class_name: count} pour toutes les classes RDD2022."""
        summary: Dict[str, int] = {name: 0 for name in RDD2022_CLASSES.values()}
        for box in boxes:
            if box.class_name in summary:
                summary[box.class_name] += 1
            else:
                summary[box.class_name] = 1
        return summary

    def _calculate_statistics(
        self,
        detections: List[Dict],
        image_shape: Tuple,
    ) -> Dict:
        """Calcule coverage, density et confiance moyenne."""
        if not detections:
            return {
                "total_area_covered":  0,
                "coverage_percentage": 0.0,
                "average_confidence":  0.0,
                "density":             0.0,
            }

        height, width = image_shape[:2]
        image_area = height * width

        total_area  = sum(d["area"] for d in detections)
        confidences = [d["confidence"] for d in detections]
        avg_conf = (
            float(np.mean(confidences))
            if np is not None
            else sum(confidences) / len(confidences)
        )

        return {
            "total_area_covered":  total_area,
            "coverage_percentage": round((total_area / image_area) * 100, 2),
            "average_confidence":  round(avg_conf, 3),
            "density":             round(len(detections) / image_area * 10_000, 2),
            "image_dimensions":    {"width": width, "height": height},
        }

    # ─────────────────────────────────────────────────────
    # Annotation image
    # ─────────────────────────────────────────────────────

    def _create_annotated_image(
        self,
        image,
        detections: List[DetectionBox],
        original_path: str,
        process_id: Optional[int] = None,
    ) -> str:
        """
        Dessine les bounding boxes RDD2022 sur l'image.
        Couleurs: orange=longitudinal, jaune=transverse,
                  rouge=alligator, bleu=pothole.
        """
        annotated = image.copy()

        for det in detections:
            color = RDD2022_COLORS.get(det.class_name, (128, 128, 128))
            label_fr = RDD2022_LABELS.get(det.class_name, det.class_name)
            label = f"{label_fr} {det.conf:.2f}"

            # Bounding box
            cv2.rectangle(
                annotated,
                (det.x1, det.y1),
                (det.x2, det.y2),
                color,
                2,
            )

            # Fond du label
            (lw, lh), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
            )
            cv2.rectangle(
                annotated,
                (det.x1, det.y1 - lh - 10),
                (det.x1 + lw, det.y1),
                color,
                -1,
            )

            # Texte label
            cv2.putText(
                annotated,
                label,
                (det.x1, det.y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
            )

        # Sauvegarde stable par process quand process_id est fourni.
        if process_id is not None:
            output_dir = Path(settings.OUTPUT_DIR) / "process" / str(process_id)
            filename = "annotated.jpg"
        else:
            output_dir = Path(settings.OUTPUT_DIR) / "detections"
            filename = Path(original_path).stem + "_annotated.jpg"

        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename
        cv2.imwrite(str(output_path), annotated)

        return str(output_path)

    # ─────────────────────────────────────────────────────
    # Format legacy (compatibilité pipeline existant)
    # ─────────────────────────────────────────────────────

    def _to_legacy_detections(self, boxes: List[DetectionBox]) -> List[Dict[str, Any]]:
        """Convertit DetectionBox → format dict attendu par le pipeline."""
        legacy = []
        for idx, box in enumerate(boxes):
            w = max(0, box.x2 - box.x1)
            h = max(0, box.y2 - box.y1)
            legacy.append(
                {
                    "id":         idx,
                    "class_id":   box.class_id,
                    "class_name": box.class_name,
                    "label_fr":   RDD2022_LABELS.get(box.class_name, box.class_name),
                    "confidence": box.conf,
                    "bbox": {
                        "x1": box.x1, "y1": box.y1,
                        "x2": box.x2, "y2": box.y2,
                        "width": w,   "height": h,
                    },
                    "area": w * h,
                }
            )
        return legacy

    # ─────────────────────────────────────────────────────
    # Batch
    # ─────────────────────────────────────────────────────

    def batch_detect(
        self,
        image_paths: List[str],
        confidence: Optional[float] = None,
    ) -> List[Dict]:
        """Détection sur plusieurs images, retourne une liste de résultats."""
        results = []
        for img_path in image_paths:
            try:
                result = self.detect_problems(
                    img_path, confidence=confidence, visualize=False
                )
                results.append({"image_path": img_path, "success": True,  "result": result})
            except Exception as exc:
                results.append({"image_path": img_path, "success": False, "error": str(exc)})
        return results


# ═══════════════════════════════════════════════════════
# Singleton + DI FastAPI
# ═══════════════════════════════════════════════════════

detection_service = DetectionService()


def get_detection_service() -> DetectionService:
    """Dependency injection FastAPI."""
    return detection_service