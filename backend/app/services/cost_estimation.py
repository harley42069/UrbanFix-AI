# app/services/cost_estimation.py

"""
Service Estimation Coûts - Llama 3.3 + Llama 4 Vision via Groq
Génère estimations détaillées travaux réaménagement en TND

Corrections v4:
- Llama 4 Vision analyse image ORIGINALE → mesures réelles de la rue
- Llama 4 Vision analyse image GÉNÉRÉE → quantifie les améliorations visibles
- Estimation finale basée sur vraies mesures + améliorations réelles
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Dict, List, Optional

try:
    from groq import Groq
except ImportError:
    Groq = None  # type: ignore[assignment,misc]

from ..core.config import settings


# ═══════════════════════════════════════════════════════
# Mapping classes RDD2022 → catégories coûts
# ═══════════════════════════════════════════════════════

RDD2022_TO_COST_CATEGORY: Dict[str, str] = {
    "longitudinal_crack": "route_degradee",
    "transverse_crack":   "route_degradee",
    "alligator_crack":    "route_degradee",
    "pothole":            "route_degradee",
    "route_degradee":           "route_degradee",
    "dechet":                   "dechet",
    "eclairage_defectueux":     "eclairage_defectueux",
    "vegetation_envahissante":  "vegetation_envahissante",
    "mobilier_casse":           "mobilier_casse",
    "graffiti":                 "graffiti",
}

# ═══════════════════════════════════════════════════════
# Base de coûts améliorations urbaines tunisiennes (TND)
# ═══════════════════════════════════════════════════════

AMELIORATIONS_COSTS_TND: Dict[str, Dict] = {
    "lampadaire_solaire":    {"prix": 1200, "unite": "unité",  "description": "Lampadaire solaire LED"},
    "lampadaire_classique":  {"prix": 450,  "unite": "unité",  "description": "Lampadaire classique"},
    "arbre":                 {"prix": 180,  "unite": "unité",  "description": "Plantation arbre"},
    "arbuste":               {"prix": 45,   "unite": "unité",  "description": "Plantation arbuste"},
    "gazon":                 {"prix": 25,   "unite": "m²",     "description": "Engazonnement"},
    "jardin_vertical":       {"prix": 350,  "unite": "m²",     "description": "Jardin vertical"},
    "fleurs":                {"prix": 35,   "unite": "m²",     "description": "Plantation fleurs"},
    "trottoir_refection":    {"prix": 180,  "unite": "m²",     "description": "Réfection trottoir"},
    "trottoir_pavage":       {"prix": 220,  "unite": "m²",     "description": "Pavage trottoir traditionnel"},
    "banc":                  {"prix": 650,  "unite": "unité",  "description": "Banc urbain"},
    "poubelle":              {"prix": 280,  "unite": "unité",  "description": "Poubelle publique"},
    "abri_bus":              {"prix": 4500, "unite": "unité",  "description": "Abri bus"},
    "piste_cyclable":        {"prix": 85,   "unite": "ml",     "description": "Piste cyclable"},
    "marquage_routier":      {"prix": 12,   "unite": "ml",     "description": "Marquage routier"},
    "refection_chaussee":    {"prix": 350,  "unite": "m²",     "description": "Réfection chaussée"},
    "parking_organise":      {"prix": 250,  "unite": "place",  "description": "Aménagement parking"},
    "glissiere_securite":    {"prix": 180,  "unite": "ml",     "description": "Glissière de sécurité"},
    "panneau_signalisation": {"prix": 320,  "unite": "unité",  "description": "Panneau signalisation"},
    "peinture_facade":       {"prix": 45,   "unite": "m²",     "description": "Peinture façade"},
    "renovation_mur":        {"prix": 120,  "unite": "m²",     "description": "Rénovation mur"},
}

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


class CostEstimationService:
    """
    Service estimation coûts avec double analyse Vision IA.

    Flux complet:
    1. Llama 4 Vision → analyse image originale (mesures réelles)
    2. YOLOv8 → détections dégradations
    3. Llama 3.3 → calcul coûts réparations
    4. Llama 4 Vision → analyse image générée (améliorations visibles)
    5. Rapport final avec coût total justifié
    """

    def __init__(self):
        self.client = None
        self.model_id = settings.GROQ_MODEL_ID
        self.temperature = settings.GROQ_TEMPERATURE
        self.max_tokens = settings.GROQ_MAX_TOKENS
        self.cost_db = settings.COST_DATABASE

    def _init_client(self) -> None:
        if Groq is None:
            raise RuntimeError("groq_not_installed: pip install groq")
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY manquante!")
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        print("✅ Client Groq initialisé")

    def _image_to_base64(self, image_path: str) -> str | None:
        """Convertit une image en base64 pour l'API Vision."""
        try:
            path = Path(image_path)
            if not path.exists():
                return None
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except Exception as exc:
            print(f"⚠️  Erreur base64 image: {exc}")
            return None

    def _get_image_mime(self, image_path: str) -> str:
        ext = Path(image_path).suffix.lower()
        return {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                "png": "image/png", "webp": "image/webp"}.get(ext.lstrip("."), "image/jpeg")

    # ─────────────────────────────────────────────────────
    # ÉTAPE 1 — Llama 4 Vision : analyse image originale
    # ─────────────────────────────────────────────────────

    def analyze_original_image(self, image_path: str) -> Dict:
        """
        Llama 4 Vision analyse l'image ORIGINALE.
        Retourne les mesures réelles de la rue.
        """
        print(f"👁️  Vision IA — analyse image originale: {Path(image_path).name}")

        if self.client is None:
            try:
                self._init_client()
            except Exception:
                return {}

        image_b64 = self._image_to_base64(image_path)
        if not image_b64:
            return {}

        mime = self._get_image_mime(image_path)
        prompt = """Analyse cette image de rue/route tunisienne.
Reponds UNIQUEMENT en JSON valide, sans texte autour:
{
  "type_espace": "rue_etroite/boulevard/autoroute/banlieue/medina/route_rurale",
  "longueur_estimee_m": 150,
  "largeur_rue_m": 6,
  "nb_poteaux_existants": 3,
  "surface_trottoirs_m2": 120,
  "surface_espaces_verts_m2": 50,
  "nb_arbres_existants": 4,
  "problemes_visibles": ["fissures", "trottoirs_degrades"],
  "contexte": "description courte de la rue en une phrase"
}"""

        try:
            response = self.client.chat.completions.create(
                model=VISION_MODEL,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{image_b64}"}
                        },
                        {"type": "text", "text": prompt}
                    ]
                }],
                max_tokens=400,
                temperature=0.1,
            )
            content = response.choices[0].message.content.strip()
            # Extraire le JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)
            print(f"✅ Vision originale: {result.get('type_espace')}, "
                  f"~{result.get('longueur_estimee_m')}m, "
                  f"{result.get('nb_poteaux_existants')} poteaux")
            return result

        except Exception as exc:
            print(f"⚠️  Vision image originale échouée: {exc}")
            return {}

    # ─────────────────────────────────────────────────────
    # ÉTAPE 4 — Llama 4 Vision : analyse image générée
    # ─────────────────────────────────────────────────────

    def analyze_generated_image(
        self,
        generated_image_path: str,
        original_analysis: Dict,
        user_prompt: str = "",
    ) -> List[Dict]:
        """
        Llama 4 Vision analyse l'image GÉNÉRÉE par SDXL.
        Compare avec l'image originale pour quantifier les améliorations.
        """
        print(f"👁️  Vision IA — analyse image générée: {Path(generated_image_path).name}")

        if self.client is None:
            try:
                self._init_client()
            except Exception:
                return []

        image_b64 = self._image_to_base64(generated_image_path)
        if not image_b64:
            return []

        mime = self._get_image_mime(generated_image_path)
        types_disponibles = ", ".join(AMELIORATIONS_COSTS_TND.keys())

        context = f"""Image originale: {original_analysis.get('type_espace', 'rue')},
longueur ~{original_analysis.get('longueur_estimee_m', 100)}m,
largeur ~{original_analysis.get('largeur_rue_m', 6)}m,
{original_analysis.get('nb_poteaux_existants', 0)} poteaux existants."""

        prompt = f"""Analyse cette image de rue rénovée/améliorée.
Contexte image originale: {context}
Demande utilisateur: {user_prompt}

Identifie les améliorations VISIBLES dans cette image.
Types disponibles: {types_disponibles}

Reponds UNIQUEMENT en JSON valide:
{{
  "ameliorations_visibles": [
    {{"type": "lampadaire_solaire", "quantite": 3, "justification": "3 lampadaires solaires visibles sur poteaux existants"}},
    {{"type": "arbre", "quantite": 6, "justification": "arbres plantés des deux côtés"}},
    {{"type": "trottoir_refection", "quantite": 120, "justification": "trottoirs rénovés ~60m × 2 côtés"}}
  ],
  "description_ameliorations": "résumé en une phrase des améliorations visibles"
}}"""

        try:
            response = self.client.chat.completions.create(
                model=VISION_MODEL,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{image_b64}"}
                        },
                        {"type": "text", "text": prompt}
                    ]
                }],
                max_tokens=500,
                temperature=0.1,
            )
            content = response.choices[0].message.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)
            ameliorations_raw = data.get("ameliorations_visibles", [])

            # Calculer les coûts
            result = []
            for item in ameliorations_raw:
                type_key = item.get("type", "")
                if type_key not in AMELIORATIONS_COSTS_TND:
                    continue
                cost_info = AMELIORATIONS_COSTS_TND[type_key]
                quantite = float(item.get("quantite") or 1)
                prix_unitaire = cost_info["prix"]
                total = round(quantite * prix_unitaire, 2)
                result.append({
                    "type":           type_key,
                    "description":    cost_info["description"],
                    "quantite":       quantite,
                    "unite":          cost_info["unite"],
                    "prix_unitaire":  prix_unitaire,
                    "total":          total,
                    "justification":  item.get("justification", ""),
                    "source":         "vision_image_generee",
                })

            print(f"Vision générée: {len(result)} amélioration(s) détectée(s)")
            return result

        except Exception as exc:
            print(f"⚠️  Vision image générée échouée: {exc}")
            return []

    # ─────────────────────────────────────────────────────
    # Calcul coûts depuis analyse image originale
    # ─────────────────────────────────────────────────────

    def _ameliorations_from_original_analysis(
        self,
        original_analysis: Dict,
        user_prompt: str = "",
    ) -> List[Dict]:
        """
        Calcule améliorations suggérées basées sur
        les mesures réelles de l'image originale.
        """
        if not original_analysis:
            return []

        if self.client is None:
            return []

        longueur = original_analysis.get("longueur_estimee_m", 100)
        largeur = original_analysis.get("largeur_rue_m", 6)
        nb_poteaux = original_analysis.get("nb_poteaux_existants", 0)
        surface_trottoirs = original_analysis.get("surface_trottoirs_m2", 0)
        surface_verts = original_analysis.get("surface_espaces_verts_m2", 0)
        type_espace = original_analysis.get("type_espace", "rue")
        types_disponibles = ", ".join(AMELIORATIONS_COSTS_TND.keys())

        prompt = f"""Tu es expert en réaménagement urbain tunisien.

Analyse de l'image originale:
- Type: {type_espace}
- Longueur visible: ~{longueur}m
- Largeur rue: ~{largeur}m  
- Poteaux existants: {nb_poteaux}
- Surface trottoirs: {surface_trottoirs}m²
- Espaces verts disponibles: {surface_verts}m²

Demande utilisateur: {user_prompt or "Améliorer cet espace urbain"}

Propose des améliorations RÉALISTES basées sur ces mesures réelles.
Types disponibles: {types_disponibles}

Reponds UNIQUEMENT en JSON:
{{
  "ameliorations": [
    {{"type": "lampadaire_solaire", "quantite": {nb_poteaux or 4}, "justification": "remplacer poteaux existants"}},
    {{"type": "trottoir_refection", "quantite": {surface_trottoirs or 100}, "justification": "surface trottoirs mesurée"}},
    {{"type": "arbre", "quantite": 8, "justification": "espaces verts disponibles"}}
  ]
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": "Expert réaménagement urbain tunisien. JSON uniquement."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=400,
                response_format={"type": "json_object"},
            )
            data = json.loads(response.choices[0].message.content)
            ameliorations_raw = data.get("ameliorations", [])

            result = []
            for item in ameliorations_raw:
                type_key = item.get("type", "")
                if type_key not in AMELIORATIONS_COSTS_TND:
                    continue
                cost_info = AMELIORATIONS_COSTS_TND[type_key]
                quantite = float(item.get("quantite", 1))
                prix_unitaire = cost_info["prix"]
                total = round(quantite * prix_unitaire, 2)
                result.append({
                    "type":          type_key,
                    "description":   cost_info["description"],
                    "quantite":      quantite,
                    "unite":         cost_info["unite"],
                    "prix_unitaire": prix_unitaire,
                    "total":         total,
                    "justification": item.get("justification", ""),
                    "source":        "analyse_image_originale",
                })

            print(f"✅ {len(result)} amélioration(s) basée(s) sur mesures réelles")
            return result

        except Exception as exc:
            print(f"⚠️  Améliorations depuis analyse originale échouées: {exc}")
            return []

    # ─────────────────────────────────────────────────────
    # Estimation principale
    # ─────────────────────────────────────────────────────

    def estimate_costs(
        self,
        detection_results: Dict,
        scenario_type: str = "moderate",
        region: str = "Tunis",
        lang: str = "fr",
        user_prompt: str | None = None,
        image_path: str | None = None,
        generated_image_path: str | None = None,
        original_image_analysis: Dict | None = None,
    ) -> Dict:
        """
        Estimation complète avec double analyse Vision IA.

        Args:
            detection_results:       Résultats YOLOv8
            scenario_type:           conservateur/modere/innovant
            region:                  Région Tunisie
            lang:                    fr/en
            user_prompt:             Prompt utilisateur
            image_path:              Chemin image originale
            generated_image_path:    Chemin image SDXL générée
            original_image_analysis: Résultat analyse Vision originale (si déjà fait)
        """
        if self.client is None:
            try:
                self._init_client()
            except Exception as exc:
                return self._fallback_estimate(
                    detection_results, scenario_type, region, lang, error=str(exc)
                )

        raw_summary = detection_results.get("summary", {})
        total_problems = detection_results.get("total_problems", 0)
        summary = self._normalize_summary(raw_summary)
        normalized_type = self._normalize_scenario_type(scenario_type)

        # ── Étape 1 : Analyse image originale ────────────────
        original_analysis = original_image_analysis or {}
        if not original_analysis and image_path:
            original_analysis = self.analyze_original_image(image_path)

        # ── Étape 2 : Coûts détections YOLOv8 ────────────────
        base_estimate = self._calculate_base_costs(
            summary, normalized_type, lang=lang,
            original_analysis=original_analysis,
        )

        # ── Étape 3 : Améliorations depuis image originale ───
        ameliorations_originale = []
        if original_analysis:
            ameliorations_originale = self._ameliorations_from_original_analysis(
                original_analysis, user_prompt or ""
            )

        # ── Étape 4 : Améliorations depuis image générée ─────
        ameliorations_generee = []
        if generated_image_path and Path(generated_image_path).exists():
            ameliorations_generee = self.analyze_generated_image(
                generated_image_path,
                original_analysis,
                user_prompt or "",
            )

        # Fusionner améliorations (image générée prioritaire)
        ameliorations_finales = ameliorations_generee if ameliorations_generee else ameliorations_originale

        # ── Étape 5 : Analyse IA texte ────────────────────────
        ai_analysis = self._get_ai_analysis(
            summary, base_estimate, normalized_type, region, lang=lang,
            original_analysis=original_analysis,
        )

        # ── Étape 6 : Calcul total ────────────────────────────
        base_total = base_estimate["total_before_management"]
        ameliorations_total = sum(a["total"] for a in ameliorations_finales)
        gestion_projet = round((base_total + ameliorations_total) * 0.10, 2)
        total_final = round(base_total + ameliorations_total + gestion_projet, 2)

        # Breakdown complet
        full_breakdown = [
            b for b in base_estimate["breakdown"]
            if b["category"] != "gestion_projet"
        ]
        for am in ameliorations_finales:
            full_breakdown.append({
                "category":      am["type"],
                "description":   am["description"],
                "quantity":      am["quantite"],
                "unit":          am["unite"],
                "unit_price":    am["prix_unitaire"],
                "total":         am["total"],
                "justification": am.get("justification", ""),
                "source":        am.get("source", "amelioration"),
            })
        full_breakdown.append({
            "category":    "gestion_projet",
            "description": "Gestion de projet (10%)" if lang == "fr" else "Project management (10%)",
            "quantity":    1,
            "unit":        "forfait",
            "unit_price":  gestion_projet,
            "total":       gestion_projet,
        })

        return {
            "total_cost_tnd":              total_final,
            "costs_by_category":           base_estimate["by_category"],
            "breakdown":                   full_breakdown,
            "breakdown_detections":        [b for b in base_estimate["breakdown"] if b["category"] != "gestion_projet"],
            "breakdown_ameliorations":     ameliorations_finales,
            "total_detections_tnd":        round(base_total, 2),
            "total_ameliorations_tnd":     round(ameliorations_total, 2),
            "total_gestion_projet_tnd":    gestion_projet,
            "scenario_type":               scenario_type,
            "scenario_type_normalized":    normalized_type,
            "region":                      region,
            "language":                    lang,
            "total_problems_detected":     total_problems,
            "ai_analysis":                 ai_analysis,
            "original_image_analysis":     original_analysis,
            "ameliorations_source":        "vision_image_generee" if ameliorations_generee else "analyse_image_originale",
            "currency":                    "TND",
            "confidence":                  "high" if ameliorations_generee else "medium",
            "rdd2022_mapping":             summary,
        }

    def _fallback_estimate(
        self,
        detection_results: Dict,
        scenario_type: str,
        region: str,
        lang: str,
        error: str = "",
    ) -> Dict:
        raw_summary = detection_results.get("summary", {})
        summary = self._normalize_summary(raw_summary)
        normalized_type = self._normalize_scenario_type(scenario_type)
        base_estimate = self._calculate_base_costs(summary, normalized_type, lang=lang)
        return {
            "total_cost_tnd":           base_estimate["total"],
            "costs_by_category":        base_estimate["by_category"],
            "breakdown":                base_estimate["breakdown"],
            "breakdown_detections":     base_estimate["breakdown"],
            "breakdown_ameliorations":  [],
            "total_detections_tnd":     base_estimate["total"],
            "total_ameliorations_tnd":  0.0,
            "total_gestion_projet_tnd": 0.0,
            "scenario_type":            scenario_type,
            "scenario_type_normalized": normalized_type,
            "region":                   region,
            "language":                 lang,
            "total_problems_detected":  detection_results.get("total_problems", 0),
            "ai_analysis": {
                "recommendations":   ["Analyse IA indisponible"],
                "risk_factors":      [],
                "cost_adjustments":  {},
                "timeline_estimate": "À définir",
                "priority_actions":  [],
                "summary":           f"Estimation basée sur règles. Erreur: {error}",
                "error":             error,
            },
            "currency":   "TND",
            "confidence": "low",
            "rdd2022_mapping": summary,
        }

    # ─────────────────────────────────────────────────────
    # Normalisation
    # ─────────────────────────────────────────────────────

    def _normalize_summary(self, summary: Dict[str, int]) -> Dict[str, int]:
        normalized: Dict[str, int] = {}
        for class_name, count in summary.items():
            if count == 0:
                continue
            category = RDD2022_TO_COST_CATEGORY.get(class_name, class_name)
            normalized[category] = normalized.get(category, 0) + count
        return normalized

    @staticmethod
    def _normalize_scenario_type(scenario_type: str) -> str:
        mapping = {
            "conservateur": "basic",  "modere": "smart",   "innovant": "premium",
            "conservative": "basic",  "moderate": "smart", "innovative": "premium",
            "basic": "basic",         "smart": "smart",    "premium": "premium",
        }
        return mapping.get(str(scenario_type or "smart").lower().strip(), "smart")

    # ─────────────────────────────────────────────────────
    # Calcul coûts de base (détections YOLOv8)
    # ─────────────────────────────────────────────────────

    def _calculate_base_costs(
        self,
        summary: Dict[str, int],
        scenario_type: str,
        lang: str = "fr",
        original_analysis: Dict | None = None,
    ) -> Dict:
        multipliers = {"basic": 1.0, "smart": 1.5, "premium": 2.5}
        multiplier = multipliers.get(scenario_type, 1.5)

        costs_by_category: Dict = {}
        breakdown: List = []
        total = 0.0

        for problem_type, count in summary.items():
            if count == 0:
                continue
            price_info = self.cost_db.get(problem_type)
            if not price_info:
                continue

            # Utiliser mesures réelles si disponibles
            quantity = self._estimate_quantity_smart(
                problem_type, count, original_analysis
            )
            unit_price = (price_info["min"] + price_info["max"]) / 2 * multiplier
            category_cost = unit_price * quantity

            costs_by_category[problem_type] = {
                "unit_price_tnd":  round(unit_price, 2),
                "quantity":        quantity,
                "unit":            price_info["unit"],
                "total_tnd":       round(category_cost, 2),
                "detected_count":  count,
            }
            breakdown.append({
                "category":    problem_type,
                "description": self._get_problem_label(problem_type, lang=lang),
                "quantity":    quantity,
                "unit":        price_info["unit"],
                "unit_price":  round(unit_price, 2),
                "total":       round(category_cost, 2),
                "source":      "detection_yolov8",
            })
            total += category_cost

        # Gestion projet provisoire
        management_cost = total * 0.10
        breakdown.append({
            "category":    "gestion_projet",
            "description": "Gestion de projet",
            "quantity":    1,
            "unit":        "forfait",
            "unit_price":  round(management_cost, 2),
            "total":       round(management_cost, 2),
        })

        return {
            "by_category":            costs_by_category,
            "breakdown":              breakdown,
            "total":                  round(total + management_cost, 2),
            "total_before_management": round(total, 2),
        }

    def _estimate_quantity_smart(
        self,
        problem_type: str,
        count: int,
        original_analysis: Dict | None = None,
    ) -> float:
        """Estime quantité en utilisant mesures réelles si disponibles."""
        if original_analysis and problem_type == "route_degradee":
            longueur = original_analysis.get("longueur_estimee_m", 0)
            largeur = original_analysis.get("largeur_rue_m", 0)
            if longueur and largeur:
                #  Surface réaliste — max 30 m² par détection
                surface_totale = longueur * largeur
                quantite = surface_totale * (count / 50)
                return round(min(quantite, 30 * count), 1)

        base_quantities = {
            "route_degradee":          10,
            "dechet":                  0.5,
            "eclairage_defectueux":    1,
            "vegetation_envahissante": 5,
            "mobilier_casse":          1,
            "graffiti":                8,
        }
        return base_quantities.get(problem_type, 1) * count
    def _get_problem_label(self, problem_type: str, lang: str = "fr") -> str:
        labels_fr = {
            "route_degradee":          "Refection chaussee/trottoirs",
            "dechet":                  "Collecte et traitement des dechets",
            "eclairage_defectueux":    "Remplacement eclairage public",
            "vegetation_envahissante": "Elagage et entretien espaces verts",
            "mobilier_casse":          "Remplacement mobilier urbain",
            "graffiti":                "Nettoyage facades et peinture",
        }
        labels_en = {
            "route_degradee":          "Road and sidewalk resurfacing",
            "dechet":                  "Waste collection and treatment",
            "eclairage_defectueux":    "Public lighting replacement",
            "vegetation_envahissante": "Green area trimming and maintenance",
            "mobilier_casse":          "Urban furniture replacement",
            "graffiti":                "Facade cleaning and repainting",
        }
        labels = labels_en if lang == "en" else labels_fr
        return labels.get(problem_type, problem_type)

    # ─────────────────────────────────────────────────────
    # Analyse IA Groq (texte)
    # ─────────────────────────────────────────────────────

    def _get_ai_analysis(
        self,
        summary: Dict,
        base_estimate: Dict,
        scenario_type: str,
        region: str,
        lang: str = "fr",
        original_analysis: Dict | None = None,
    ) -> Dict:
        problems_text = "\n".join([
            f"- {self._get_problem_label(k, lang=lang)}: {v} detection(s)"
            for k, v in summary.items() if v > 0
        ]) or ("Aucun problème détecté" if lang == "fr" else "No issues detected")

        context_vision = ""
        if original_analysis:
            context_vision = f"""
Analyse Vision IA de l'espace:
- Type: {original_analysis.get('type_espace', 'N/A')}
- Longueur: ~{original_analysis.get('longueur_estimee_m', 'N/A')}m
- Largeur: ~{original_analysis.get('largeur_rue_m', 'N/A')}m
- Poteaux existants: {original_analysis.get('nb_poteaux_existants', 0)}
- Trottoirs: {original_analysis.get('surface_trottoirs_m2', 0)}m²"""

        total_cost = base_estimate["total"]
        system_content = (
            "Tu es un expert en reamenagement urbain tunisien. "
            "Reponds UNIQUEMENT en JSON valide."
        )
        prompt = f"""Analyse ce projet de reamenagement urbain tunisien:
Region: {region}, Scenario: {scenario_type}
Estimation base: {total_cost:,.2f} TND
Problemes detectes: {problems_text}
{context_vision}

JSON avec: recommendations, risk_factors, cost_adjustments, timeline_estimate, priority_actions, summary"""

        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user",   "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},
            )
            ai_data = json.loads(response.choices[0].message.content)
            return {
                "recommendations":   ai_data.get("recommendations", []),
                "risk_factors":      ai_data.get("risk_factors", []),
                "cost_adjustments":  ai_data.get("cost_adjustments", {}),
                "timeline_estimate": ai_data.get("timeline_estimate", ""),
                "priority_actions":  ai_data.get("priority_actions", []),
                "summary":           ai_data.get("summary", ""),
                "model_used":        self.model_id,
            }
        except Exception as exc:
            print(f"⚠️  Erreur analyse IA Groq: {exc}")
            return {
                "recommendations":   ["Analyse IA indisponible"],
                "risk_factors":      [],
                "cost_adjustments":  {},
                "timeline_estimate": "À définir",
                "priority_actions":  [],
                "summary":           "Estimation basée sur règles uniquement",
                "error":             str(exc),
            }

    def generate_detailed_report_text(self, estimation: Dict) -> str:
        lines = [
            "=" * 65,
            "     ESTIMATION DÉTAILLÉE RÉAMÉNAGEMENT URBAIN - UrbanFix AI",
            "=" * 65,
            f"Région: {estimation.get('region', 'Tunis')}",
            f"Scénario: {estimation.get('scenario_type', '').upper()}",
            f"Confiance: {estimation.get('confidence', 'medium').upper()}",
        ]

        original = estimation.get("original_image_analysis", {})
        if original:
            lines += [
                "",
                "📍 ANALYSE VISION IA (image originale):",
                f"   Type d'espace: {original.get('type_espace', 'N/A')}",
                f"   Dimensions: ~{original.get('longueur_estimee_m')}m × {original.get('largeur_rue_m')}m",
                f"   Poteaux existants: {original.get('nb_poteaux_existants', 0)}",
                f"   Surface trottoirs: {original.get('surface_trottoirs_m2', 0)}m²",
            ]

        lines += ["", "1. TRAVAUX SUR DÉTECTIONS (YOLOv8):", "-" * 65]
        for item in estimation.get("breakdown_detections", []):
            lines.append(
                f"   {item['description']:<35} {item['quantity']:>6.1f} {item['unit']:<8} "
                f"× {item['unit_price']:>8.2f} = {item['total']:>10.2f} TND"
            )

        ameliorations = estimation.get("breakdown_ameliorations", [])
        source = estimation.get("ameliorations_source", "")
        if ameliorations:
            source_label = "Vision image générée" if "generee" in source else "Analyse image originale"
            lines += ["", f"2. AMÉLIORATIONS DÉTECTÉES ({source_label}):", "-" * 65]
            for item in ameliorations:
                lines.append(
                    f"   {item['description']:<35} {item['quantite']:>6.1f} {item['unite']:<8} "
                    f"× {item['prix_unitaire']:>8.2f} = {item['total']:>10.2f} TND"
                )
                if item.get("justification"):
                    lines.append(f"   → {item['justification']}")

        lines += [
            "",
            "-" * 65,
            f"   Réparations (YOLOv8):     {estimation.get('total_detections_tnd', 0):>10.2f} TND",
            f"   Améliorations (Vision):   {estimation.get('total_ameliorations_tnd', 0):>10.2f} TND",
            f"   Gestion projet (10%):     {estimation.get('total_gestion_projet_tnd', 0):>10.2f} TND",
            "=" * 65,
            f"   TOTAL ESTIMÉ:             {estimation.get('total_cost_tnd', 0):>10.2f} TND",
            "=" * 65,
        ]
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# Singleton + DI FastAPI
# ═══════════════════════════════════════════════════════

cost_estimation_service = CostEstimationService()


def get_cost_estimation_service() -> CostEstimationService:
    return cost_estimation_service