from __future__ import annotations

from app.api.endpoints import process as process_ep
from app.models.signalement import Signalement, SignalementStatus


def test_trigger_pipeline_then_status_processing(
    client,
    auth_headers,
    fake_image_file,
    db_session_factory,
    monkeypatch,
):
    # Create signalement first
    sig_data = {
        "title": "Décharge sauvage",
        "description": "Accumulation de déchets",
        "latitude": "36.81",
        "longitude": "10.17",
        "address": "Quartier test",
        "city": "Tunis",
        "region": "Tunis",
    }
    sig_files = {"image": ("pipeline.jpg", fake_image_file, "image/jpeg")}
    created = client.post("/api/v1/signalements/", data=sig_data, files=sig_files, headers=auth_headers)
    assert created.status_code == 201, created.text
    signalement_id = created.json()["data"]["id"]

    # Patch queue trigger to simulate worker moving job to processing
    def _fake_enqueue(sig_id: int, background_tasks=None, **_kwargs):
        db = db_session_factory()
        try:
            sig = db.query(Signalement).filter(Signalement.id == sig_id).first()
            sig.status = SignalementStatus.PROCESSING
            sig.progress = 15
            sig.current_stage = "detection"
            db.add(sig)
            db.commit()
        finally:
            db.close()
        return {"queued": True, "mode": "mock", "task_id": "mock-task-1"}

    monkeypatch.setattr(process_ep, "enqueue_signalement_processing", _fake_enqueue)

    trigger = client.post(f"/api/v1/process/{signalement_id}", headers=auth_headers)
    assert trigger.status_code == 202, trigger.text

    status_resp = client.get(f"/api/v1/process/{signalement_id}/status", headers=auth_headers)
    assert status_resp.status_code == 200, status_resp.text
    body = status_resp.json()
    assert body["success"] is True
    assert body["data"]["status"] == "processing"
    assert body["data"]["stage"] == "detection"
    assert body["data"]["progress"] >= 15
