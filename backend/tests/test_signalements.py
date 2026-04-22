from __future__ import annotations

from app.services.orchestrator import OrchestratorService
from app.core.config import settings


def test_create_signalement_with_fake_upload(client, auth_headers, fake_image_file):
    data = {
        "title": "Nid de poule avenue Habib Bourguiba",
        "description": "Chaussée dégradée",
        "latitude": "36.8065",
        "longitude": "10.1815",
        "address": "Centre-ville",
        "city": "Tunis",
        "region": "Tunis",
        "metadata": '{"source": "test"}',
    }
    files = {"image": ("fake.jpg", fake_image_file, "image/jpeg")}

    response = client.post(
        "/api/v1/signalements/",
        data=data,
        files=files,
        headers=auth_headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["success"] is True
    assert body["data"]["title"] == data["title"]
    assert body["data"]["status"] == "pending"
    assert body["data"]["progress"] == 0


def test_prompt_only_creates_signalement_and_status_returns_scenarios(
    client,
    auth_headers,
    db_session_factory,
    monkeypatch,
):
    from app.api.endpoints import signalements as signalements_ep

    def _sync_enqueue(
        signalement_id,
        background_tasks=None,
        user_prompt=None,
        generate_media=False,
        interaction_mode="prompt_only",
        category="roads",
        generate_audio=False,
        generate_video=False,
        generate_pdf=False,
        **_kwargs,
    ):
        db = db_session_factory()
        try:
            orchestrator = OrchestratorService()
            orchestrator.process_signalement_db(
                db=db,
                signalement_id=signalement_id,
                user_prompt=user_prompt,
                generate_media=generate_media,
                interaction_mode=interaction_mode,
                category=category,
                generate_audio=generate_audio,
                generate_video=generate_video,
                generate_pdf=generate_pdf,
                mock_services=True,
            )
        finally:
            db.close()
        return {"queued": True, "mode": "sync-test", "task_id": "sync-task"}

    monkeypatch.setattr(signalements_ep, "enqueue_signalement_processing", _sync_enqueue)

    payload = {
        "title": "Prompt only test",
        "description": "Sans image, mais avec prompt",
        "interaction_mode": "prompt_only",
        "category": "roads",
        "user_prompt": "Generate 3 urban improvement scenarios",
        "latitude": 36.8,
        "longitude": 10.18,
        "generate_audio": True,
    }
    create_resp = client.post("/api/v1/signalements/prompt", json=payload, headers=auth_headers)
    assert create_resp.status_code == 201, create_resp.text

    body = create_resp.json()
    assert body["success"] is True
    signalement_id = body["data"]["signalement_id"]

    status_resp = client.get(f"/api/v1/process/{signalement_id}/status", headers=auth_headers)
    assert status_resp.status_code == 200, status_resp.text
    status_data = status_resp.json()["data"]
    assert status_data["interaction_mode"] == "prompt_only"
    assert status_data["category"] == "roads"
    assert isinstance(status_data["results"]["scenarios"], list)
    assert len(status_data["results"]["scenarios"]) >= 1


def test_photo_only_still_works_no_regression(client, auth_headers, fake_image_file):
    data = {
        "title": "Regression photo only",
        "description": "Signalement avec photo",
        "latitude": "36.8065",
        "longitude": "10.1815",
        "address": "Centre-ville",
        "city": "Tunis",
        "region": "Tunis",
        "metadata": '{"interaction_mode": "photo_only", "category": "roads"}',
    }
    files = {"image": ("photo_only.jpg", fake_image_file, "image/jpeg")}
    create_resp = client.post("/api/v1/signalements/", data=data, files=files, headers=auth_headers)
    assert create_resp.status_code == 201, create_resp.text
    signalement_id = create_resp.json()["data"]["id"]

    trigger = client.post(
        f"/api/v1/process/{signalement_id}",
        json={
            "interaction_mode": "photo_only",
            "category": "roads",
            "user_prompt": "Optional prompt",
            "generate_audio": True,
        },
        headers=auth_headers,
    )
    assert trigger.status_code == 202, trigger.text
    trigger_data = trigger.json()["data"]
    assert trigger_data["interaction_mode"] == "photo_only"
    assert trigger_data["category"] == "roads"
    assert trigger_data["generate_media"] is True


def test_guest_prompt_only_allowed_when_allow_guest_true(client, monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_GUEST", True)

    payload = {
        "title": "Guest prompt",
        "interaction_mode": "prompt_only",
        "category": "roads",
        "user_prompt": "Generate scenarios from text only",
    }

    response = client.post("/api/v1/signalements/prompt", json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["success"] is True


def test_guest_prompt_only_denied_when_allow_guest_false(client, monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_GUEST", False)

    payload = {
        "title": "Guest prompt denied",
        "interaction_mode": "prompt_only",
        "category": "roads",
        "user_prompt": "Generate scenarios from text only",
    }

    response = client.post("/api/v1/signalements/prompt", json=payload)
    assert response.status_code == 401, response.text
    body = response.json()
    if "error" in body and body["error"]:
        assert body["error"]["message"] == "Not authenticated"
    else:
        assert body["detail"] == "Not authenticated"


def test_guest_multipart_image_upload_allowed_when_allow_guest_true(
    client, monkeypatch, fake_image_file
):
    """Test that guest user can upload image via multipart without bcrypt errors on Windows/Python 3.12."""
    monkeypatch.setattr(settings, "ALLOW_GUEST", True)

    data = {
        "title": "Guest image upload",
        "latitude": "36.8065",
        "longitude": "10.1815",
        "city": "Tunis",
        "region": "Tunis",
        "metadata": '{"interaction_mode": "photo_only", "category": "drainage"}',
    }
    files = {"image": ("guest_upload.jpg", fake_image_file, "image/jpeg")}

    response = client.post("/api/v1/signalements/", data=data, files=files)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["success"] is True
    assert body["data"]["title"] == "Guest image upload"
    # Verify guest owner was created (user_id should be set)
    assert body["data"]["user_id"] is not None

