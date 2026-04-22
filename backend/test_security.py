"""Unit tests for security hardening (auth, RBAC, upload validation)."""

from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace

from fastapi import Depends, FastAPI, UploadFile
from fastapi.testclient import TestClient

from app.api import dependencies as deps
from app.core.upload_validation import validate_image_upload
from app.db.session import get_db


class _DummyDb:
    def query(self, *_args, **_kwargs):
        return self

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return None


def _override_get_db():
    yield _DummyDb()


def test_invalid_token_returns_401(monkeypatch):
    """Invalid/expired access token should return HTTP 401."""
    app = FastAPI()

    @app.get("/secure")
    async def secure_route(_user=Depends(deps.get_current_user)):
        return {"ok": True}

    app.dependency_overrides[get_db] = _override_get_db
    monkeypatch.setattr(deps, "verify_token", lambda *_args, **_kwargs: None)

    client = TestClient(app)
    response = client.get("/secure", headers={"Authorization": "Bearer invalid.token"})

    assert response.status_code == 401


def test_citizen_forbidden_on_admin_endpoint():
    """Citizen role must be forbidden on admin-only endpoint."""
    app = FastAPI()

    @app.get("/admin")
    async def admin_route(_user=Depends(deps.require_role(["admin"]))):
        return {"ok": True}

    async def _fake_current_user():
        return SimpleNamespace(id=1, role="citizen")

    app.dependency_overrides[deps.get_current_user] = _fake_current_user

    client = TestClient(app)
    response = client.get("/admin")

    assert response.status_code == 403


def test_upload_over_10mb_returns_413():
    """Upload larger than configured MAX_UPLOAD_SIZE should return 413."""
    app = FastAPI()

    @app.post("/upload")
    async def upload(file: UploadFile):
        validate_image_upload(file)
        return {"ok": True}

    client = TestClient(app)

    payload = BytesIO(b"a" * (10 * 1024 * 1024 + 1))
    files = {"file": ("too_big.jpg", payload, "image/jpeg")}
    response = client.post("/upload", files=files)

    assert response.status_code == 413
