from __future__ import annotations

from app.models.detection import Detection
from app.models.signalement import Signalement


def test_estimation_mocked_services(client, auth_headers, fake_image_file, db_session):
    # 1) Create signalement via API
    sig_data = {
        "title": "Lampadaire cassé",
        "description": "Eclairage défaillant",
        "latitude": "36.80",
        "longitude": "10.18",
        "address": "Rue test",
        "city": "Tunis",
        "region": "Tunis",
    }
    sig_files = {"image": ("sig.jpg", fake_image_file, "image/jpeg")}
    created = client.post("/api/v1/signalements/", data=sig_data, files=sig_files, headers=auth_headers)
    assert created.status_code == 201, created.text
    signalement_id = created.json()["data"]["id"]

    # 2) Insert a detection row so estimation endpoint can proceed
    detection = Detection(
        signalement_id=signalement_id,
        class_name="route_degradee",
        confidence=0.91,
        bbox_x=0.1,
        bbox_y=0.2,
        bbox_width=0.3,
        bbox_height=0.4,
    )
    db_session.add(detection)
    db_session.commit()

    # 3) Call estimation endpoint (Groq is mocked in conftest)
    payload = {
        "signalement_id": signalement_id,
        "scenario_types": ["minimal", "moderate"],
        "generate_images": False,
    }
    response = client.post(
        f"/api/v1/estimation/{signalement_id}",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["data"]["recommended"] == "moderate"
    assert body["data"]["minimal"] is not None
