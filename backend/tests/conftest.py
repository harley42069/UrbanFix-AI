"""Pytest fixtures for offline API tests with temporary SQLite DB and mocked externals."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Patch huggingface_hub before any diffusers imports occur
import sys
try:
    from huggingface_hub import hf_hub_download, model_info
except ImportError:
    pass

# Lazy import endpoints to avoid triggering heavy AI dependencies
from app.core.config import settings
from app.core.handlers import register_exception_handlers
from app.db.base import Base
from app.db.session import get_db
from app.models import detection, estimation, signalement, user  # noqa: F401

# Patch bcrypt context globally to avoid Windows passlib issues
from app.core import security as security_module

class MockHash:
    """Mock hash that avoids bcrypt backend initialization."""
    def __init__(self, password):
        self.password = password
        
    def __eq__(self, other):
        return other == f"hashed_{self.password}"
    
    def __str__(self):
        return f"hashed_{self.password}"
    
    def __repr__(self):
        return f"hashed_{self.password}"

def _mock_hash(password):
    return f"hashed_{password}"

def _mock_verify(plain, hashed):
    return hashed == f"hashed_{plain}"

# Replace the context methods
security_module.pwd_context.hash = _mock_hash
security_module.pwd_context.verify = _mock_verify
security_module.get_password_hash = _mock_hash
security_module.verify_password = _mock_verify


@pytest.fixture(scope="function")
def db_session_factory(tmp_path):
    """Build a per-test SQLite database and return a session factory."""
    db_file = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    try:
        yield TestingSessionLocal
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_session_factory) -> Session:
    session = db_session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session_factory):
    """TestClient with overridden get_db dependency using temporary SQLite."""
    # Lazy import endpoints here to avoid triggering heavy AI dependencies
    from app.api.endpoints import auth, estimation as estimation_ep, process, signalements

    test_app = FastAPI()
    register_exception_handlers(test_app)
    test_app.include_router(auth.router, prefix="/api/v1/auth")
    test_app.include_router(signalements.router, prefix="/api/v1/signalements")
    test_app.include_router(estimation_ep.router, prefix="/api/v1/estimation")
    test_app.include_router(process.router, prefix="/api/v1/process")

    def _override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    test_app.dependency_overrides[get_db] = _override_get_db

    with TestClient(test_app) as c:
        yield c

    test_app.dependency_overrides.clear()


@pytest.fixture(scope="function", autouse=True)
def mock_external_services(monkeypatch, tmp_path):
    """Mock network-dependent AI services so tests run fully offline."""
    uploads_dir = tmp_path / "uploads"
    outputs_dir = tmp_path / "outputs"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    (outputs_dir / "scenarios").mkdir(parents=True, exist_ok=True)
    (outputs_dir / "audio").mkdir(parents=True, exist_ok=True)
    (outputs_dir / "videos").mkdir(parents=True, exist_ok=True)
    (outputs_dir / "reports").mkdir(parents=True, exist_ok=True)
    (outputs_dir / "detections").mkdir(parents=True, exist_ok=True)

    scenario_path = outputs_dir / "scenarios" / "scenario_mock.png"
    audio_path = outputs_dir / "audio" / "audio_mock.wav"
    video_path = outputs_dir / "videos" / "video_mock.mp4"
    report_path = outputs_dir / "reports" / "report_mock.pdf"
    annotated_path = outputs_dir / "detections" / "annotated_mock.jpg"

    scenario_path.write_bytes(b"fake-image")
    audio_path.write_bytes(b"fake-audio")
    video_path.write_bytes(b"fake-video")
    report_path.write_bytes(b"%PDF-1.4 fake")
    annotated_path.write_bytes(b"fake-annotated")

    monkeypatch.setattr(settings, "UPLOADS_DIR", str(uploads_dir))
    monkeypatch.setattr(settings, "OUTPUTS_DIR", str(outputs_dir))
    monkeypatch.setattr(settings, "OUTPUT_DIR", str(outputs_dir))

    # Groq/Llama mocks
    from app.services import cost_estimation as cost_module

    monkeypatch.setattr(cost_module.CostEstimationService, "_init_client", lambda self: None)

    def _mock_estimate_costs(self, detection_results, scenario_type="moderate", region="Tunis", lang="fr"):
        return {
            "total_min": 1000.0,
            "total_max": 2000.0,
            "total_avg": 1500.0,
            "total_cost_tnd": 1500.0,
            "breakdown": {"route_degradee": {"cost": 1500.0}},
            "duration_days": 7,
            "priority_score": 0.5,
            "description": f"Mock estimation for {scenario_type} in {region}",
            "language": lang,
        }

    monkeypatch.setattr(cost_module.CostEstimationService, "estimate_costs", _mock_estimate_costs)

    # Heavy modules (image/audio/video/detection) are intentionally not imported
    # here to keep tests stable on environments without torch/torchaudio binaries.

    # PDF mock
    try:
        from app.services import pdf_report as pdf_module

        monkeypatch.setattr(
            pdf_module.PDFReportService,
            "generate_complete_report",
            lambda self, *_args, **_kwargs: {"success": True, "pdf_path": str(report_path), "file_size_mb": 0.1},
        )
    except Exception:
        pass

    _ = (scenario_path, audio_path, video_path, report_path, annotated_path)

    # Default pipeline enqueue no-op for deterministic tests.
    from app.api.endpoints import process as process_ep
    from app.api.endpoints import signalements as signalements_ep

    noop_enqueue = lambda signalement_id, background_tasks=None, user_prompt=None, generate_media=False, **_kwargs: {
        "queued": True,
        "mode": "test-noop",
        "task_id": None,
    }
    monkeypatch.setattr(process_ep, "enqueue_signalement_processing", noop_enqueue)
    monkeypatch.setattr(signalements_ep, "enqueue_signalement_processing", noop_enqueue)


@pytest.fixture(scope="function")
def fake_image_file():
    """Return an in-memory valid JPEG file for multipart upload tests."""
    img = Image.new("RGB", (32, 32), color=(255, 0, 0))
    data = BytesIO()
    img.save(data, format="JPEG")
    data.seek(0)
    return data


@pytest.fixture(scope="function")
def auth_headers(client):
    """Create a citizen user and return bearer auth headers."""
    register_payload = {
        "email": "citizen@example.com",
        "username": "citizen_user",
        "password": "Test1234",
        "full_name": "Citizen User",
        "role": "citizen",
    }
    reg = client.post("/api/v1/auth/register", json=register_payload)
    assert reg.status_code == 201, reg.text

    login = client.post(
        "/api/v1/auth/login",
        data={"username": "citizen_user", "password": "Test1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200, login.text
    access_token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {access_token}"}
