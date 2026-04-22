# app/services/pdf_report.py

"""
Service Génération Rapports PDF - ReportLab
Corrections v6:
- Suppression coût sous scénario Premium
- Suppression summary dict dans recommandations
- Fix titres scénarios par index
- Fix timeline dict → string
- Fix actions dict → string
"""

from __future__ import annotations

import os
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Image,
        KeepTogether,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    warnings.warn("reportlab non installé. pip install reportlab")
    A4 = (595.27, 841.89)
    cm = 28.35

from ..core.config import settings


_LABELS_FR: Dict[str, str] = {
    "longitudinal_crack": "Fissure longitudinale",
    "transverse_crack":   "Fissure transversale",
    "alligator_crack":    "Fissure en crocodile",
    "pothole":            "Nid-de-poule",
    "route_degradee":           "Chaussee/trottoirs degrades",
    "dechet":                   "Accumulation de dechets",
    "eclairage_defectueux":     "Eclairage public defectueux",
    "vegetation_envahissante":  "Vegetation envahissante",
    "mobilier_casse":           "Mobilier urbain endommage",
    "graffiti":                 "Graffitis/tags",
}

_LABELS_EN: Dict[str, str] = {
    "longitudinal_crack": "Longitudinal crack",
    "transverse_crack":   "Transverse crack",
    "alligator_crack":    "Alligator crack",
    "pothole":            "Pothole",
    "route_degradee":           "Degraded roads/sidewalks",
    "dechet":                   "Waste accumulation",
    "eclairage_defectueux":     "Faulty public lighting",
    "vegetation_envahissante":  "Overgrown vegetation",
    "mobilier_casse":           "Damaged street furniture",
    "graffiti":                 "Graffiti/tags",
}

_PRIORITY_MAP: Dict[str, str] = {
    "longitudinal_crack": "Haute",
    "transverse_crack":   "Haute",
    "alligator_crack":    "Haute",
    "pothole":            "Haute",
    "route_degradee":           "Haute",
    "dechet":                   "Haute",
    "eclairage_defectueux":     "Moyenne",
    "vegetation_envahissante":  "Moyenne",
    "mobilier_casse":           "Moyenne",
    "graffiti":                 "Basse",
}

SCENARIO_LABELS_FR = {
    "basic": "Scénario Basique (Conservateur)",
    "smart": "Scénario Smart (Recommandé)",
    "premium": "Scénario Premium (Innovant)",
    "conservateur": "Scénario Basique (Conservateur)",
    "modere": "Scénario Smart (Recommandé)",
    "innovant": "Scénario Premium (Innovant)",
}

SCENARIO_LABELS_EN = {
    "basic": "Basic Scenario (Conservative)",
    "smart": "Smart Scenario (Recommended)",
    "premium": "Premium Scenario (Innovative)",
    "conservateur": "Basic Scenario (Conservative)",
    "modere": "Smart Scenario (Recommended)",
    "innovant": "Premium Scenario (Innovative)",
}

SCENARIO_TITLES_BY_INDEX_FR = {
    0: "Scénario Basique (Conservateur)",
    1: "Scénario Smart (Recommandé)",
    2: "Scénario Premium (Innovant)",
}

SCENARIO_TITLES_BY_INDEX_EN = {
    0: "Basic Scenario (Conservative)",
    1: "Smart Scenario (Recommended)",
    2: "Premium Scenario (Innovative)",
}

SCENARIO_MULTIPLIERS = {
    "basic": 1.0, "conservateur": 1.0,
    "smart": 1.5, "modere": 1.5,
    "premium": 2.5, "innovant": 2.5,
}


def _safe_str(value) -> str:
    """Convertit n'importe quelle valeur en string propre."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("description", "action", "text", "label", "value", "summary"):
            if key in value:
                v = value[key]
                if isinstance(v, str):
                    return v
        # Si le dict ne contient pas de clé connue, ignorer
        return ""
    if isinstance(value, list):
        return ", ".join(_safe_str(v) for v in value if v)
    return str(value)


def _safe_timeline(value) -> str:
    """Convertit une timeline (str ou dict) en string lisible."""
    if not value:
        return "À définir"
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        duree = value.get("duree") or value.get("total_duration") or value.get("duration", "")
        unite = value.get("unite") or value.get("unit", "mois")
        if duree:
            return f"{duree} {unite}"
        debut = value.get("debut", "")
        fin = value.get("fin", "")
        if debut and fin:
            return f"{debut} → {fin}"
    return "À définir"


class PDFReportService:

    def __init__(self):
        self.page_width, self.page_height = A4
        self._lang = "fr"
        self.output_base = Path(settings.OUTPUT_DIR)

        if REPORTLAB_AVAILABLE:
            self.styles = getSampleStyleSheet()
            self._setup_custom_styles()
        else:
            self.styles = None

    def _setup_custom_styles(self) -> None:
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#1a5490'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
        ))
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c7bb6'),
            spaceBefore=15,
            spaceAfter=10,
            fontName='Helvetica-Bold',
        ))
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading3'],
            fontSize=13,
            textColor=colors.HexColor('#1a5490'),
            spaceBefore=12,
            spaceAfter=8,
            fontName='Helvetica-Bold',
        ))
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=10,
            leading=14,
        ))
        self.styles.add(ParagraphStyle(
            name='Caption',
            parent=self.styles['BodyText'],
            fontSize=9,
            textColor=colors.grey,
            alignment=TA_CENTER,
            spaceAfter=8,
            fontName='Helvetica-Oblique',
        ))

    def _resolve_image_path(self, path_or_url: str | None) -> str | None:
        if not path_or_url:
            return None
        p = str(path_or_url).replace("\\", "/")
        if p.startswith("http://") or p.startswith("https://"):
            if "/static/outputs/" in p:
                local = p.split("/static/outputs/")[1]
                candidate = self.output_base / local
                if candidate.exists():
                    return str(candidate)
            if "/outputs/" in p:
                local = p.split("/outputs/")[1]
                candidate = self.output_base / local
                if candidate.exists():
                    return str(candidate)
            return None
        if Path(p).is_absolute() and Path(p).exists():
            return p
        candidate = self.output_base.parent / p.lstrip("/")
        if candidate.exists():
            return str(candidate)
        candidate2 = Path(p)
        if candidate2.exists():
            return str(candidate2)
        candidate3 = Path("backend") / p.lstrip("/")
        if candidate3.exists():
            return str(candidate3)
        candidate4 = Path("outputs") / p.lstrip("/").replace("outputs/", "")
        if candidate4.exists():
            return str(candidate4)
        candidate5 = Path(settings.OUTPUT_DIR).parent / p.lstrip("/")
        if candidate5.exists():
            return str(candidate5)
        return None

    def generate_complete_report(
        self,
        project_data: Dict,
        detection_results: Dict,
        scenarios: List[Dict],
        cost_estimation: Dict,
        output_filename: str = "rapport_urbanfix",
        lang: str = "fr",
        selected_scenario_type: str | None = None,
    ) -> Dict:
        if not REPORTLAB_AVAILABLE:
            return {"success": False, "pdf_path": None,
                    "error": "reportlab_not_installed: pip install reportlab"}
        self._lang = lang
        try:
            print("📄 Génération rapport PDF...")
            output_dir = Path(settings.OUTPUT_DIR) / "reports"
            output_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"{output_filename}_{ts}.pdf"

            filtered_scenarios = scenarios
            selected_label = None
            if selected_scenario_type:
                filtered_scenarios = [
                    s for s in scenarios
                    if (s.get("scenario_type") == selected_scenario_type
                        or s.get("type") == selected_scenario_type)
                ]
                if not filtered_scenarios:
                    filtered_scenarios = scenarios[:1]
                labels = SCENARIO_LABELS_EN if lang == "en" else SCENARIO_LABELS_FR
                selected_label = labels.get(selected_scenario_type, selected_scenario_type)

            doc = SimpleDocTemplate(
                str(output_path), pagesize=A4,
                rightMargin=2*cm, leftMargin=2*cm,
                topMargin=2.5*cm, bottomMargin=2*cm,
            )
            story: List = []
            story.extend(self._create_cover_page(project_data, lang=lang, selected_label=selected_label))
            story.append(PageBreak())
            story.extend(self._create_executive_summary(detection_results, cost_estimation, lang=lang, selected_scenario_type=selected_scenario_type))
            story.append(PageBreak())
            story.extend(self._create_detection_section(detection_results, lang=lang))
            story.append(PageBreak())
            story.extend(self._create_scenarios_section(filtered_scenarios, lang=lang))
            story.append(PageBreak())
            story.extend(self._create_cost_section(cost_estimation, lang=lang, selected_scenario_type=selected_scenario_type))
            story.append(PageBreak())
            story.extend(self._create_recommendations_section(cost_estimation, lang=lang))
            story.append(PageBreak())
            story.extend(self._create_appendices(project_data, lang=lang))

            doc.build(story, onFirstPage=self._header_footer_callback, onLaterPages=self._header_footer_callback)
            file_size = os.path.getsize(output_path)
            print(f"✅ Rapport PDF généré: {output_path}")
            return {"success": True, "pdf_path": str(output_path),
                    "file_size_mb": round(file_size / 1024 / 1024, 2), "format": "PDF/A4"}

        except Exception as exc:
            print(f"❌ Erreur génération PDF: {exc}")
            import traceback; traceback.print_exc()
            return {"success": False, "pdf_path": None, "error": str(exc)}

    def _header_footer_callback(self, canvas_obj, doc) -> None:
        self._add_header_footer(canvas_obj, doc, lang=self._lang)

    def _add_header_footer(self, canvas_obj, doc, lang: str = "fr") -> None:
        canvas_obj.saveState()
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.setFillColor(colors.HexColor("#2c7bb6"))
        canvas_obj.rect(2*cm, self.page_height - 1.2*cm, self.page_width - 4*cm, 0.02*cm, fill=1)
        canvas_obj.setFillColor(colors.grey)
        date_str = datetime.now().strftime("%d/%m/%Y")
        canvas_obj.drawString(2*cm, 0.8*cm, f"UrbanFix AI - Rapport genere le {date_str}")
        canvas_obj.drawRightString(self.page_width - 2*cm, 0.8*cm, f"Page {canvas_obj.getPageNumber()}")
        canvas_obj.restoreState()

    def _create_cover_page(self, project_data: Dict, lang: str = "fr", selected_label: str | None = None) -> List:
        elements: List = []
        elements.append(Spacer(1, 3*cm))
        elements.append(Paragraph("RAPPORT D'ANALYSE ET RÉAMÉNAGEMENT URBAIN", self.styles["CustomTitle"]))
        if selected_label:
            elements.append(Paragraph(f"Scénario sélectionné: {selected_label}", self.styles["CustomSubtitle"]))
        elements.append(Spacer(1, 1.5*cm))
        project_title = project_data.get("title", "Projet de reamenagement")
        location = project_data.get("location", "Tunisie")
        date = project_data.get("date", datetime.now().strftime("%d/%m/%Y"))
        info = (
            f"<b>Projet:</b> {project_title}<br/>"
            f"<b>Localisation:</b> {location}<br/>"
            f"<b>Date:</b> {date}<br/>"
            f"<b>Généré par:</b> UrbanFix AI"
        )
        elements.append(Paragraph(info, self.styles["CustomBody"]))
        elements.append(Spacer(1, 2*cm))
        tech_text = ("<b>Technologies IA utilisées:</b> YOLOv8 • SDXL + LoRA tnrenovation • "
                     "Llama 4 Vision • Llama 3.3 70B (Groq) • Bark TTS")
        elements.append(Paragraph(tech_text, self.styles["Caption"]))
        return elements

    def _create_executive_summary(self, detection_results: Dict, cost_estimation: Dict,
                                   lang: str = "fr", selected_scenario_type: str | None = None) -> List:
        elements: List = []
        elements.append(Paragraph("1. RÉSUMÉ EXÉCUTIF", self.styles["CustomTitle"]))

        total_problems = detection_results.get("total_problems", 0)
        multiplier = SCENARIO_MULTIPLIERS.get(selected_scenario_type or "smart", 1.5)
        base_total = cost_estimation.get("total_detections_tnd", 0)
        amelio_total = cost_estimation.get("total_ameliorations_tnd", 0)
        gestion = round((base_total + amelio_total) * multiplier * 0.10, 2)
        total_cost = round((base_total + amelio_total) * multiplier + gestion, 2)
        if total_cost == 0:
            total_cost = cost_estimation.get("total_cost_tnd", 0)

        timeline_raw = cost_estimation.get("ai_analysis", {}).get("timeline_estimate", "")
        timeline = _safe_timeline(timeline_raw)

        vision_data = cost_estimation.get("original_image_analysis", {})
        vision_info = ""
        if vision_data:
            type_espace = vision_data.get("type_espace", "")
            longueur = vision_data.get("longueur_estimee_m", "")
            largeur = vision_data.get("largeur_rue_m", "")
            poteaux = vision_data.get("nb_poteaux_existants", 0)
            vision_info = (
                f" L'analyse Vision IA a identifié un espace de type <b>{type_espace}</b> "
                f"d'environ <b>{longueur}m</b> × <b>{largeur}m</b>, "
                f"avec <b>{poteaux}</b> poteaux existants."
            )

        summary_text = (
            f"Ce rapport présente une analyse complète par IA d'un espace urbain tunisien. "
            f"Nous avons identifié <b>{total_problems} problème(s)</b> nécessitant une intervention.{vision_info} "
            f"L'estimation budgétaire totale s'élève à <b>{total_cost:,.2f} TND</b>."
        )
        elements.append(Paragraph(summary_text, self.styles["CustomBody"]))
        elements.append(Spacer(1, 0.5*cm))

        scenario_label = SCENARIO_LABELS_FR.get(selected_scenario_type or "smart", "Smart")
        summary_data = [
            ["Indicateur", "Valeur"],
            ["Problèmes détectés", str(total_problems)],
            ["Scénario sélectionné", scenario_label],
            ["Réparations (YOLOv8)", f"{base_total * multiplier:,.2f} TND"],
            ["Améliorations (Vision IA)", f"{amelio_total * multiplier:,.2f} TND"],
            ["Gestion de projet (10%)", f"{gestion:,.2f} TND"],
            ["TOTAL ESTIMÉ", f"{total_cost:,.2f} TND"],
            ["Délai estimé", timeline],
        ]

        t = Table(summary_data, colWidths=[10*cm, 7*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#2c7bb6")),
            ("TEXTCOLOR",     (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME",      (0, -2), (-1, -2), "Helvetica-Bold"),
            ("BACKGROUND",    (0, -2), (-1, -2), colors.HexColor("#1a5490")),
            ("TEXTCOLOR",     (0, -2), (-1, -2), colors.whitesmoke),
            ("GRID",          (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS",(0, 1), (-1, -3), [colors.white, colors.HexColor("#f0f4f8")]),
        ]))
        elements.append(t)
        return elements

    def _create_detection_section(self, detection_results: Dict, lang: str = "fr") -> List:
        elements: List = []
        elements.append(Paragraph("2. ANALYSE DES DÉTECTIONS (YOLOv8)", self.styles["CustomTitle"]))
        elements.append(Paragraph(
            "L'analyse automatisée par YOLOv8 (entraîné sur le dataset RDD2022) "
            "a identifié et localisé les dégradations de la chaussée.",
            self.styles["CustomBody"]
        ))

        summary = detection_results.get("summary", {})
        if summary:
            data = [["Type de problème", "Nombre détecté", "Priorité"]]
            for problem_type, count in summary.items():
                if count == 0:
                    continue
                label = self._get_problem_label(problem_type, lang=lang)
                priority = _PRIORITY_MAP.get(problem_type, "Moyenne")
                data.append([label, str(count), priority])
            t = Table(data, colWidths=[10*cm, 3*cm, 4*cm])
            t.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#2c7bb6")),
                ("TEXTCOLOR",     (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID",          (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f8")]),
            ]))
            elements.append(t)
        else:
            elements.append(Paragraph("Aucune dégradation détectée.", self.styles["CustomBody"]))

        elements.append(Spacer(1, 0.5*cm))

        annotated = (detection_results.get("annotated_image")
                     or detection_results.get("annotated_image_path")
                     or detection_results.get("annotated_image_url"))
        img_resolved = self._resolve_image_path(annotated)
        if img_resolved:
            elements.append(Paragraph("2.1 Visualisation des détections", self.styles["SectionHeader"]))
            try:
                elements.append(Image(img_resolved, width=14*cm, height=9*cm))
                elements.append(Paragraph(
                    "<i>Figure 1: Image originale avec détections YOLOv8</i>",
                    self.styles["Caption"],
                ))
            except Exception as e:
                print(f"⚠️ Image annotée non chargée: {e}")

        return elements

    def _create_scenarios_section(self, scenarios: List[Dict], lang: str = "fr") -> List:
        elements: List = []
        elements.append(Paragraph(
            "3. SCÉNARIOS DE RÉAMÉNAGEMENT (SDXL + LoRA)",
            self.styles["CustomTitle"],
        ))
        nb = len(scenarios)
        elements.append(Paragraph(
            f"{nb} scénario(s) de réaménagement généré(s) par IA (SDXL + LoRA tnrenovation + Groq).",
            self.styles["CustomBody"],
        ))
        elements.append(Spacer(1, 0.5*cm))

        titles_by_index = SCENARIO_TITLES_BY_INDEX_FR

        for i, scenario in enumerate(scenarios):
            title = titles_by_index.get(i, f"Scénario {i+1}")
            elements.append(Paragraph(f"3.{i+1} {title}", self.styles["SectionHeader"]))
            elements.append(Spacer(1, 0.3*cm))

            img_path = scenario.get("image_path")
            if not img_path or not Path(str(img_path)).exists():
                img_path = scenario.get("image_url")
            img_resolved = self._resolve_image_path(img_path)
            print(f"🔍 Image scénario {i+1}: {img_path} → {img_resolved}")

            if img_resolved:
                try:
                    elements.append(Image(img_resolved, width=14*cm, height=10*cm))
                    elements.append(Paragraph(
                        f"<i>Figure {i+2}: {title} — Généré par SDXL + LoRA tnrenovation</i>",
                        self.styles["Caption"],
                    ))
                except Exception as e:
                    print(f"⚠️ Image scénario {i+1} non chargée: {e}")
            else:
                elements.append(Paragraph("<i>Image non générée</i>", self.styles["Caption"]))

            # ✅ Aucun coût affiché sous les scénarios
            elements.append(Spacer(1, 1*cm))

        return elements

    def _create_cost_section(self, cost_estimation: Dict, lang: str = "fr",
                              selected_scenario_type: str | None = None) -> List:
        elements: List = []
        elements.append(Paragraph("4. ESTIMATION BUDGÉTAIRE DÉTAILLÉE", self.styles["CustomTitle"]))

        multiplier = SCENARIO_MULTIPLIERS.get(selected_scenario_type or "smart", 1.5)
        scenario_label = SCENARIO_LABELS_FR.get(selected_scenario_type or "smart", "Smart")

        elements.append(Paragraph(
            f"<b>Scénario:</b> {scenario_label} (multiplicateur ×{multiplier})",
            self.styles["CustomBody"],
        ))

        vision = cost_estimation.get("original_image_analysis", {})
        if vision:
            vision_text = (
                f"<b>Analyse Vision IA:</b> {vision.get('type_espace', 'N/A')} | "
                f"~{vision.get('longueur_estimee_m', 'N/A')}m × {vision.get('largeur_rue_m', 'N/A')}m | "
                f"{vision.get('nb_poteaux_existants', 0)} poteaux | "
                f"{vision.get('surface_trottoirs_m2', 0)}m² trottoirs"
            )
            elements.append(Paragraph(vision_text, self.styles["Caption"]))

        elements.append(Spacer(1, 0.5*cm))
        header = ["Poste", "Qté", "Unité", "Prix Unit. (TND)", "Total (TND)"]

        # Section A
        elements.append(Paragraph("A. Réparations Chaussée (Détections YOLOv8)", self.styles["SectionHeader"]))
        detections_breakdown = cost_estimation.get("breakdown_detections", [])
        if detections_breakdown:
            cost_data = [header]
            subtotal = 0.0
            for item in detections_breakdown:
                if item.get("category") == "gestion_projet":
                    continue
                up = item.get("unit_price", 0) * multiplier
                tot = item.get("total", 0) * multiplier
                subtotal += tot
                cost_data.append([
                    _safe_str(item.get("description", "")),
                    f"{item.get('quantity', 0):.1f}",
                    _safe_str(item.get("unit", "")),
                    f"{up:.2f}", f"{tot:.2f}",
                ])
            cost_data.append(["", "", "", "Sous-total", f"{subtotal:.2f}"])
            elements.append(self._make_cost_table(cost_data))
        else:
            elements.append(Paragraph("Aucune réparation requise.", self.styles["CustomBody"]))

        elements.append(Spacer(1, 0.5*cm))

        # Section B
        elements.append(Paragraph("B. Améliorations Urbaines (Analyse Vision IA)", self.styles["SectionHeader"]))
        amelio_breakdown = cost_estimation.get("breakdown_ameliorations", [])
        if amelio_breakdown:
            amelio_source = cost_estimation.get("ameliorations_source", "")
            source_note = ("Source: Llama 4 Vision — analyse image scénario généré"
                          if "generee" in amelio_source
                          else "Source: Llama 4 Vision — analyse image originale")
            elements.append(Paragraph(f"<i>{source_note}</i>", self.styles["Caption"]))
            cost_data = [header]
            subtotal = 0.0
            for item in amelio_breakdown:
                up = item.get("prix_unitaire", 0) * multiplier
                tot = item.get("total", 0) * multiplier
                subtotal += tot
                cost_data.append([
                    _safe_str(item.get("description", "")),
                    f"{item.get('quantite', 0):.1f}",
                    _safe_str(item.get("unite", "")),
                    f"{up:.2f}", f"{tot:.2f}",
                ])
                just = item.get("justification", "")
                if just:
                    cost_data.append([f"  → {_safe_str(just)}", "", "", "", ""])
            cost_data.append(["", "", "", "Sous-total", f"{subtotal:.2f}"])
            elements.append(self._make_cost_table(cost_data))
        else:
            elements.append(Paragraph("Aucune amélioration détectée.", self.styles["CustomBody"]))

        elements.append(Spacer(1, 0.5*cm))

        det_total = cost_estimation.get("total_detections_tnd", 0) * multiplier
        am_total  = cost_estimation.get("total_ameliorations_tnd", 0) * multiplier
        gestion   = round((det_total + am_total) * 0.10, 2)
        total_final = round(det_total + am_total + gestion, 2)
        if total_final == 0:
            total_final = cost_estimation.get("total_cost_tnd", 0)

        total_data = [
            ["Réparations (YOLOv8)",      f"{det_total:,.2f} TND"],
            ["Améliorations (Vision IA)", f"{am_total:,.2f} TND"],
            ["Gestion de projet (10%)",   f"{gestion:,.2f} TND"],
            ["TOTAL ESTIMÉ",              f"{total_final:,.2f} TND"],
        ]
        t_total = Table(total_data, colWidths=[12*cm, 5*cm])
        t_total.setStyle(TableStyle([
            ("GRID",       (0, 0), (-1, -2), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 0), (-1, -2), [colors.white, colors.HexColor("#f0f4f8")]),
            ("FONTNAME",   (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#1a5490")),
            ("TEXTCOLOR",  (0, -1), (-1, -1), colors.whitesmoke),
            ("FONTSIZE",   (0, -1), (-1, -1), 12),
            ("ALIGN",      (1, 0), (1, -1), "RIGHT"),
        ]))
        elements.append(t_total)
        return elements

    def _make_cost_table(self, data: List) -> Table:
        t = Table(data, colWidths=[6*cm, 2*cm, 2*cm, 3*cm, 3*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#2c7bb6")),
            ("TEXTCOLOR",     (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME",      (0, -1), (-1, -1), "Helvetica-Bold"),
            ("ALIGN",         (1, 1), (-1, -1), "RIGHT"),
            ("GRID",          (0, 0), (-1, -2), 0.5, colors.grey),
            ("LINEABOVE",     (0, -1), (-1, -1), 1.5, colors.HexColor("#2c7bb6")),
            ("BACKGROUND",    (0, -1), (-1, -1), colors.HexColor("#dce8f5")),
            ("ROWBACKGROUNDS",(0, 1), (-1, -2), [colors.white, colors.HexColor("#f0f4f8")]),
            ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ]))
        return t

    def _create_recommendations_section(self, cost_estimation: Dict, lang: str = "fr") -> List:
        elements: List = []
        elements.append(Paragraph("5. RECOMMANDATIONS", self.styles["CustomTitle"]))

        ai = cost_estimation.get("ai_analysis", {})

        # ✅ Summary — ignorer si c'est un dict (données brutes Groq)
        summary = ai.get("summary", "")
        if isinstance(summary, str) and summary.strip():
            elements.append(Paragraph(summary, self.styles["CustomBody"]))
            elements.append(Spacer(1, 0.5*cm))
        # Si dict → on ne l'affiche pas (données brutes non formatées)

        # Recommandations
        recommendations = ai.get("recommendations", [])
        if recommendations:
            elements.append(Paragraph("<b>Recommandations principales:</b>", self.styles["CustomBody"]))
            for i, rec in enumerate(recommendations, 1):
                rec_str = _safe_str(rec)
                if rec_str:
                    elements.append(Paragraph(f"<b>{i}.</b> {rec_str}", self.styles["CustomBody"]))

        # Actions prioritaires
        priority_actions = ai.get("priority_actions", [])
        if priority_actions:
            elements.append(Spacer(1, 0.3*cm))
            elements.append(Paragraph("<b>Actions prioritaires:</b>", self.styles["CustomBody"]))
            for action in priority_actions:
                action_str = _safe_str(action)
                if action_str:
                    elements.append(Paragraph(f"• {action_str}", self.styles["CustomBody"]))

        # Timeline
        timeline_raw = ai.get("timeline_estimate", "")
        timeline = _safe_timeline(timeline_raw)
        if timeline and timeline != "À définir":
            elements.append(Spacer(1, 0.3*cm))
            elements.append(Paragraph(f"<b>Durée estimée:</b> {timeline}", self.styles["CustomBody"]))

        if not recommendations:
            elements.append(Paragraph("Aucune recommandation spécifique générée.", self.styles["CustomBody"]))

        return elements

    def _create_appendices(self, project_data: Dict, lang: str = "fr") -> List:
        elements: List = []
        elements.append(Paragraph("6. ANNEXES TECHNIQUES", self.styles["CustomTitle"]))
        text = (
            "<b>6.1 Méthodologie</b><br/>"
            "Ce rapport a été généré automatiquement par UrbanFix AI en utilisant:<br/>"
            "• <b>YOLOv8</b>: Détection dégradations routières (dataset RDD2022 — 4 classes)<br/>"
            "• <b>SDXL + LoRA tnrenovation</b>: Génération scénarios photoréalistes<br/>"
            "• <b>Llama 4 Vision</b>: Analyse spatiale image originale et scénario généré<br/>"
            "• <b>Llama 3.3 70B (Groq)</b>: Estimation coûts et recommandations<br/>"
            "• <b>Bark TTS</b>: Narration audio IA<br/><br/>"
            "<b>6.2 Limites et précautions</b><br/>"
            "Les estimations fournies sont indicatives et basées sur des moyennes tunisiennes. "
            "Une étude technique approfondie reste nécessaire avant tout engagement financier."
        )
        elements.append(Paragraph(text, self.styles["CustomBody"]))
        return elements

    def _get_problem_label(self, problem_type: str, lang: str = "fr") -> str:
        labels = _LABELS_EN if lang == "en" else _LABELS_FR
        return labels.get(problem_type, problem_type.replace("_", " "))


pdf_report_service = PDFReportService()


def get_pdf_report_service() -> PDFReportService:
    return pdf_report_service