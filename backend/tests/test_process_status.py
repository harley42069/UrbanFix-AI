"""Tests end-to-end pour les endpoints process (POST trigger + GET status).

Ces tests vérifient :
- POST /api/v1/process/{id} déclenche le pipeline (mock noop)
- GET  /api/v1/process/{id}/status retourne la structure attendue
- Les colonnes JSON (detections/scenarios/estimations) et URLs sont bien lues
- Les cas d'erreur (404, 403, pipeline déjà en cours) se comportent correctement.

Toutes les dépendances IA sont mockées par le fixture autouse ``mock_external_services``
de conftest.py ; les tests s'exécutent entièrement hors-ligne.
"""

from __future__ import annotations

import pytest

from app.api.endpoints import process as process_ep
from app.models.signalement import Signalement, SignalementStatus
from app.repositories.signalement_repo import (
    save_pipeline_results,
    update_signalement_status,
)
from app.services.orchestrator import OrchestratorService


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _create_signalement(client, auth_headers, fake_image_file) -> int:
    """Crée un signalement via l'API et retourne son identifiant."""
    fake_image_file.seek(0)
    data = {
        "title": "Nid de poule test pipeline",
        "latitude": "36.8065",
        "longitude": "10.1815",
        "city": "Tunis",
        "region": "Tunis",
    }
    files = {"image": ("test.jpg", fake_image_file, "image/jpeg")}
    resp = client.post(
        "/api/v1/signalements/",
        data=data,
        files=files,
        headers=auth_headers,
    )
    assert resp.status_code == 201, f"Création signalement échouée: {resp.text}"
    return resp.json()["data"]["id"]


# ─────────────────────────────────────────────────────────────────────────────
# Tests POST /api/v1/process/{id}
# ─────────────────────────────────────────────────────────────────────────────


def test_trigger_pipeline_returns_202(client, auth_headers, fake_image_file):
    """POST déclenche le pipeline et retourne 202 avec les infos de file d'attente."""
    sig_id = _create_signalement(client, auth_headers, fake_image_file)

    resp = client.post(f"/api/v1/process/{sig_id}", headers=auth_headers)

    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["signalement_id"] == sig_id
    assert data["queued"] is True
    assert data["status"] == "pending"
    assert "queue_mode" in data


def test_trigger_pipeline_with_generate_media_flag(client, auth_headers, fake_image_file):
    """POST accepte le corps JSON avec user_prompt et generate_media."""
    sig_id = _create_signalement(client, auth_headers, fake_image_file)

    resp = client.post(
        f"/api/v1/process/{sig_id}",
        json={"user_prompt": "Améliorer la chaussée", "generate_media": True},
        headers=auth_headers,
    )

    assert resp.status_code == 202, resp.text
    assert resp.json()["success"] is True


def test_trigger_pipeline_already_processing(client, db_session_factory, auth_headers, fake_image_file):
    """POST est idempotent : si status=PROCESSING, retourne 202 sans re-queue."""
    sig_id = _create_signalement(client, auth_headers, fake_image_file)

    # Passer en PROCESSING directement en DB
    db = db_session_factory()
    try:
        update_signalement_status(
            db, sig_id,
            status=SignalementStatus.PROCESSING,
            progress=15,
            stage="detection",
        )
    finally:
        db.close()

    resp = client.post(f"/api/v1/process/{sig_id}", headers=auth_headers)

    assert resp.status_code == 202, resp.text
    data = resp.json()["data"]
    assert data["queued"] is False
    assert data["status"] == "processing"


def test_trigger_pipeline_not_found(client, auth_headers):
    """POST sur un identifiant inexistant retourne 404."""
    resp = client.post("/api/v1/process/99999", headers=auth_headers)
    assert resp.status_code == 404, resp.text
    assert resp.json()["success"] is False


def test_trigger_pipeline_unauthorized(client, auth_headers, fake_image_file):
    """Un second utilisateur ne peut pas déclencher le pipeline d'un autre."""
    sig_id = _create_signalement(client, auth_headers, fake_image_file)

    # Créer un second utilisateur
    other_reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "other@example.com",
            "username": "other_user",
            "password": "Test1234",
            "full_name": "Other",
            "role": "citizen",
        },
    )
    assert other_reg.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "other_user", "password": "Test1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    other_token = login.json()["data"]["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    resp = client.post(f"/api/v1/process/{sig_id}", headers=other_headers)
    assert resp.status_code == 403, resp.text
    assert resp.json()["success"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Tests GET /api/v1/process/{id}/status
# ─────────────────────────────────────────────────────────────────────────────


def test_get_status_structure_pending(client, auth_headers, fake_image_file):
    """GET /status retourne tous les champs attendus pour un signalement en attente."""
    sig_id = _create_signalement(client, auth_headers, fake_image_file)

    resp = client.get(f"/api/v1/process/{sig_id}/status", headers=auth_headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True

    data = body["data"]
    # Champs obligatoires
    assert data["signalement_id"] == sig_id
    assert data["status"] in ("pending", "processing", "completed", "failed")
    assert isinstance(data["progress"], int)
    assert "current_stage" in data
    assert "last_error" in data
    assert "completed_at" in data
    assert "processing_time_seconds" in data
    assert "interaction_mode" in data
    assert "category" in data
    # Résultats IA (nuls au départ)
    assert "results" in data
    assert isinstance(data["results"], dict)
    for key in ("detections", "scenarios", "media"):
        assert key in data["results"]
    assert "interaction_mode" in data["results"]
    assert "category" in data["results"]
    assert "detections" in data
    assert "scenarios" in data
    assert "estimations" in data
    # Outputs
    assert "outputs" in data
    assert isinstance(data["outputs"], dict)
    for key in ("annotated_image", "annotated_image_path", "scenario_image", "audio", "video", "pdf"):
        assert key in data["outputs"]
    # Canal WebSocket
    assert "ws_channel" in data
    assert str(sig_id) in data["ws_channel"]


def test_get_status_after_manual_completion(client, db_session_factory, auth_headers, fake_image_file):
    """GET /status expose les résultats IA et URLs après exécution du pipeline."""
    sig_id = _create_signalement(client, auth_headers, fake_image_file)

    # Simuler la fin du pipeline en écrivant directement en DB
    mock_detections = {
        "total_problems": 2,
        "detections": [{"class_name": "route_degradee", "confidence": 0.91}],
    }
    mock_scenarios = {
        "items": [
            {"type": "minimal", "image_path": "/outputs/scenarios/s1.png"},
            {"type": "moderate", "image_path": "/outputs/scenarios/s2.png"},
        ],
        "selected": {"type": "moderate"},
    }
    mock_estimations = {
        "total_avg": 9500.0,
        "total_min": 7000.0,
        "total_max": 12000.0,
        "duration_days": 5,
    }

    db = db_session_factory()
    try:
        save_pipeline_results(
            db,
            sig_id,
            detections=mock_detections,
            scenarios=mock_scenarios,
            estimations=mock_estimations,
            audio_url="/outputs/audio/narration.wav",
            video_url="/outputs/videos/transformation.mp4",
            pdf_url="/outputs/reports/rapport.pdf",
            processing_time=14.7,
        )
        update_signalement_status(
            db, sig_id,
            status=SignalementStatus.COMPLETED,
            progress=100,
            stage="completed",
            last_error=None,
        )
    finally:
        db.close()

    resp = client.get(f"/api/v1/process/{sig_id}/status", headers=auth_headers)

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]

    assert data["status"] == "completed"
    assert data["progress"] == 100
    assert data["current_stage"] == "completed"
    assert data["last_error"] is None
    assert data["processing_time_seconds"] == pytest.approx(14.7)

    # Résultats IA
    assert data["detections"]["total_problems"] == 2
    assert isinstance(data["scenarios"], list)
    assert len(data["scenarios"]) == 2
    assert data["scenarios"][0]["scenario_type"] in ("basic", "smart", "premium")
    assert data["estimations"]["total_avg"] == pytest.approx(9500.0)
    assert isinstance(data["results"]["scenarios"], list)
    assert data["results"]["media"]["pdf"] == "/outputs/reports/rapport.pdf"

    # URLs médias
    assert data["outputs"]["audio"] == "/outputs/audio/narration.wav"
    assert data["outputs"]["video"] == "/outputs/videos/transformation.mp4"


def test_smoke_status_fallback_detection_result_without_ultralytics_dependency(
    client,
    db_session_factory,
    auth_headers,
    fake_image_file,
    monkeypatch,
):
    """Smoke test: /process then /status must expose fallback detections schema."""
    sig_id = _create_signalement(client, auth_headers, fake_image_file)

    def _fake_enqueue(sig_id: int, background_tasks=None, **_kwargs):
        db = db_session_factory()
        try:
            fallback_detection = {
                "model_name": "yolov8",
                "model_version": "best.pt",
                "image_width": 0,
                "image_height": 0,
                "boxes": [],
                "warnings": ["yolo_model_not_found: ./models/best.pt"],
                "detections": [],
                "summary": {},
                "statistics": {
                    "total_area_covered": 0,
                    "coverage_percentage": 0.0,
                    "average_confidence": 0.0,
                    "density": 0.0,
                },
                "annotated_image": None,
                "total_problems": 0,
            }
            save_pipeline_results(db, sig_id, detections=fallback_detection)
            update_signalement_status(
                db,
                sig_id,
                status=SignalementStatus.COMPLETED,
                progress=100,
                stage="completed",
                last_error=None,
            )
        finally:
            db.close()
        return {"queued": True, "mode": "mock", "task_id": "mock-fallback-det"}

    monkeypatch.setattr(process_ep, "enqueue_signalement_processing", _fake_enqueue)

    trigger = client.post(f"/api/v1/process/{sig_id}", headers=auth_headers)
    assert trigger.status_code == 202, trigger.text

    status_resp = client.get(f"/api/v1/process/{sig_id}/status", headers=auth_headers)
    assert status_resp.status_code == 200, status_resp.text
    data = status_resp.json()["data"]

    assert data["status"] == "completed"
    assert data["detections"]["boxes"] == []
    assert data["detections"]["warnings"]
    assert "yolo_model_not_found:" in data["detections"]["warnings"][0]
    assert data["detection_result"]["boxes"] == []
    assert data["results"]["detections"]["boxes"] == []
    assert data["results"]["detection_result"]["boxes"] == []


def test_get_status_after_failure(client, db_session_factory, auth_headers, fake_image_file):
    """GET /status retourne status='failed' avec last_error renseigné."""
    sig_id = _create_signalement(client, auth_headers, fake_image_file)

    db = db_session_factory()
    try:
        update_signalement_status(
            db,
            sig_id,
            status=SignalementStatus.FAILED,
            progress=20,
            stage="failed",
            last_error={"stage": "images", "message": "Replicate API timeout"},
        )
    finally:
        db.close()

    resp = client.get(f"/api/v1/process/{sig_id}/status", headers=auth_headers)

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["status"] == "failed"
    assert data["last_error"]["stage"] == "images"
    assert data["last_error"]["message"] == "Replicate API timeout"


def test_get_status_not_found(client, auth_headers):
    """GET /status sur un signalement inexistant retourne 404."""
    resp = client.get("/api/v1/process/99999/status", headers=auth_headers)
    assert resp.status_code == 404, resp.text
    assert resp.json()["success"] is False


def test_get_status_unauthorized(client, auth_headers, fake_image_file):
    """Un autre utilisateur ne peut pas consulter le status d'un signalement."""
    sig_id = _create_signalement(client, auth_headers, fake_image_file)

    other_reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "spy@example.com",
            "username": "spy_user",
            "password": "Test1234",
            "full_name": "Spy",
            "role": "citizen",
        },
    )
    assert other_reg.status_code == 201
    spy_login = client.post(
        "/api/v1/auth/login",
        data={"username": "spy_user", "password": "Test1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    spy_token = spy_login.json()["data"]["access_token"]
    spy_headers = {"Authorization": f"Bearer {spy_token}"}

    resp = client.get(f"/api/v1/process/{sig_id}/status", headers=spy_headers)
    assert resp.status_code == 403, resp.text


def test_status_schema_contains_scenarios_fields(
    client, db_session_factory, auth_headers, fake_image_file
):
    """Le status expose results.scenarios avec tous les champs obligatoires du schema Scenario."""
    sig_id = _create_signalement(client, auth_headers, fake_image_file)

    mock_scenarios = [
        {
            "id": "scn-1",
            "scenario_type": "basic",
            "title": "Scenario basique",
            "description": "Reparation minimale de la voirie",
            "prompt_used": "urban repair basic",
            "image_url": "/outputs/scenarios/s1.png",
            "narration_text": "Scenario basique avec intervention rapide.",
            "actions": [{"label": "Reparer la voirie"}],
            "cost_breakdown": [
                {
                    "category": "route_degradee",
                    "description": "Refection chaussee",
                    "quantity": 1,
                    "unit": "forfait",
                    "unit_price": 5000,
                    "total": 5000,
                }
            ],
            "cost_total": 5000,
        }
    ]

    db = db_session_factory()
    try:
        save_pipeline_results(
            db,
            sig_id,
            detections={"total_problems": 1},
            scenarios=mock_scenarios,
            estimations={"total_cost_tnd": 5000},
        )
        update_signalement_status(
            db,
            sig_id,
            status=SignalementStatus.COMPLETED,
            progress=100,
            stage="completed",
            last_error=None,
        )
    finally:
        db.close()

    resp = client.get(f"/api/v1/process/{sig_id}/status", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    scenarios = resp.json()["data"]["results"]["scenarios"]
    assert isinstance(scenarios, list)
    assert len(scenarios) == 1
    scenario = scenarios[0]
    for field_name in (
        "id",
        "scenario_type",
        "title",
        "description",
        "prompt_used",
        "image_url",
        "narration_text",
        "actions",
        "cost_breakdown",
        "cost_total",
    ):
        assert field_name in scenario


def test_prompt_english_generates_english_narration_in_status(
    client, db_session_factory, auth_headers, fake_image_file
):
    """Prompt EN -> narration_text EN + language='en' dans le status."""
    sig_id = _create_signalement(client, auth_headers, fake_image_file)

    db = db_session_factory()
    try:
        orchestrator = OrchestratorService()
        result = orchestrator.process_signalement_db(
            db=db,
            signalement_id=sig_id,
            user_prompt="Please redesign this street and estimate the cost.",
            generate_media=False,
            mock_services=True,
        )
        assert result["ok"] is True
    finally:
        db.close()

    resp = client.get(f"/api/v1/process/{sig_id}/status", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["language"] == "en"
    assert data["results"]["language"] == "en"
    narration = data["results"]["scenarios"][0]["narration_text"]
    lowered = narration.lower()
    assert "this" in lowered
    assert "will" in lowered
    assert "cost" in lowered


def test_prompt_french_generates_french_narration_in_status(
    client, db_session_factory, auth_headers, fake_image_file
):
    """Prompt FR -> narration_text FR + language='fr' dans le status."""
    sig_id = _create_signalement(client, auth_headers, fake_image_file)

    db = db_session_factory()
    try:
        orchestrator = OrchestratorService()
        result = orchestrator.process_signalement_db(
            db=db,
            signalement_id=sig_id,
            user_prompt="Je veux ameliorer cette rue et estimer le cout des travaux.",
            generate_media=False,
            mock_services=True,
        )
        assert result["ok"] is True
    finally:
        db.close()

    resp = client.get(f"/api/v1/process/{sig_id}/status", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["language"] == "fr"
    assert data["results"]["language"] == "fr"
    narration = data["results"]["scenarios"][0]["narration_text"].lower()
    assert "ce" in narration
    assert "cout" in narration
    assert "travaux" in narration
