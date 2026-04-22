"""Pydantic schema and helpers for a stable multimodal Scenario payload."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ScenarioType(str, Enum):
    """Canonical scenario families exposed by the API."""

    BASIC = "basic"
    SMART = "smart"
    PREMIUM = "premium"


class CostItem(BaseModel):
    """Single cost line attached to a scenario."""

    category: str = Field(..., description="Internal cost category key")
    description: str = Field(..., description="Human readable label")
    quantity: float = Field(..., ge=0)
    unit: str = Field(..., description="Unit name, e.g. m2, unit, forfait")
    unit_price: float = Field(..., ge=0)
    total: float = Field(..., ge=0)


class ScenarioAction(BaseModel):
    """Action item planned in a scenario."""

    label: str = Field(..., min_length=2, max_length=200)
    details: str | None = Field(default=None, max_length=500)


class Scenario(BaseModel):
    """Stable scenario format used across DB, status API, and media generation."""

    id: str 
    scenario_type: ScenarioType
    title: str
    description: str
    prompt_used: str
    image_url: str | None = None
    narration_text: str
    actions: list[ScenarioAction] = Field(default_factory=list)
    cost_breakdown: list[CostItem] = Field(default_factory=list)
    cost_total: float = Field(default=0, ge=0)


_SCENARIO_TYPE_ALIASES: dict[str, ScenarioType] = {
    "basic": ScenarioType.BASIC,
    "minimal": ScenarioType.BASIC,
    "conservative": ScenarioType.BASIC,
    "smart": ScenarioType.SMART,
    "moderate": ScenarioType.SMART,
    "balanced": ScenarioType.SMART,
    "premium": ScenarioType.PREMIUM,
    "innovative": ScenarioType.PREMIUM,
}


def normalize_scenario_type(value: Any) -> ScenarioType:
    """Map legacy scenario types to the canonical enum."""

    if isinstance(value, ScenarioType):
        return value
    key = str(value or "smart").strip().lower()
    return _SCENARIO_TYPE_ALIASES.get(key, ScenarioType.SMART)


def _normalize_breakdown_row(item: dict[str, Any]) -> CostItem:
    """Normalize one heterogeneous estimation row to CostItem."""

    quantity = float(item.get("quantity", item.get("count", 1)) or 1)
    unit_price = float(item.get("unit_price", item.get("unit_cost", 0)) or 0)
    total = item.get("total", item.get("cost", quantity * unit_price))

    return CostItem(
        category=str(item.get("category") or item.get("key") or "travaux"),
        description=str(item.get("description") or item.get("label") or "Travaux urbains"),
        quantity=max(0.0, quantity),
        unit=str(item.get("unit") or "unit"),
        unit_price=max(0.0, float(unit_price)),
        total=max(0.0, float(total or 0)),
    )


def normalize_cost_breakdown(estimations: dict[str, Any] | None) -> tuple[list[CostItem], float]:
    """Return canonical cost breakdown and total from heterogeneous estimation payloads."""

    if not estimations:
        return [], 0.0

    breakdown = estimations.get("breakdown")
    items: list[CostItem] = []

    if isinstance(breakdown, list):
        for row in breakdown:
            if isinstance(row, dict):
                items.append(_normalize_breakdown_row(row))
    elif isinstance(breakdown, dict):
        for key, row in breakdown.items():
            if isinstance(row, dict):
                payload = dict(row)
                payload.setdefault("category", key)
                payload.setdefault("description", key.replace("_", " ").title())
                items.append(_normalize_breakdown_row(payload))

    total = float(
        estimations.get("total_cost_tnd")
        or estimations.get("total_avg")
        or estimations.get("total")
        or sum(item.total for item in items)
    )

    return items, max(0.0, total)


def build_narration_text(
    title: str,
    description: str,
    actions: list[ScenarioAction],
    cost_total: float,
    lang: str = "fr",
) -> str:
    """Compose a short narration used consistently by audio and PDF."""

    action_text = "; ".join(action.label for action in actions[:3])
    if lang == "en":
        return (
            f"This scenario is {title}. {description} "
            f"This plan will include: {action_text}. "
            f"This work will cost about {cost_total:,.0f} TND."
        )
    return (
        f"Ce scenario est {title}. {description} "
        f"Les travaux prevus sont: {action_text}. "
        f"Le cout estime est de {cost_total:,.0f} TND."
    )


def normalize_scenarios_payload(
    raw_scenarios: Any,
    estimations: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Normalize old/new scenario payloads to Scenario[]."""

    if isinstance(raw_scenarios, dict):
        candidates = raw_scenarios.get("items", [])
    elif isinstance(raw_scenarios, list):
        candidates = raw_scenarios
    else:
        candidates = []

    cost_items, cost_total = normalize_cost_breakdown(estimations)
    normalized: list[dict[str, Any]] = []

    for idx, entry in enumerate(candidates, start=1):
        if not isinstance(entry, dict):
            continue

        scenario_type = normalize_scenario_type(
            entry.get("scenario_type") or entry.get("type")
        )
        title = str(entry.get("title") or f"Scenario {scenario_type.value.title()}")
        description = str(
            entry.get("description")
            or "Reamenagement urbain avec amelioration de la voirie et des espaces publics."
        )

        raw_actions = entry.get("actions") if isinstance(entry.get("actions"), list) else []
        actions = [
            ScenarioAction(
                label=str(item.get("label") or item.get("title") or "Intervention prioritaire"),
                details=(str(item.get("details")) if item.get("details") else None),
            )
            for item in raw_actions
            if isinstance(item, dict)
        ]
        if not actions:
            actions = [
                ScenarioAction(label="Reparer la voirie"),
                ScenarioAction(label="Mettre a niveau l'eclairage public"),
                ScenarioAction(label="Securiser la zone pietonne"),
            ]

        prompt_used = str(entry.get("prompt_used") or entry.get("prompt") or "")
        image_url = entry.get("image_url") or entry.get("image_path")
        narration_text = str(
            entry.get("narration_text")
            or build_narration_text(title, description, actions, cost_total)
        )

        scenario = Scenario(
            id=str(entry.get("id") or f"scn-{idx}"),
            scenario_type=scenario_type,
            title=title,
            description=description,
            prompt_used=prompt_used,
            image_url=(str(image_url) if image_url else None),
            narration_text=narration_text,
            actions=actions,
            cost_breakdown=cost_items,
            cost_total=cost_total,
        )
        normalized.append(scenario.model_dump())

    return normalized
