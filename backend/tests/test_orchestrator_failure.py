"""Tests de la gestion d'erreurs dans process_signalement_db().

Ces tests forcent une exception dans une étape précise du pipeline (en
patchant un service IA avec ``unittest.mock.patch``) et vérifient que
l'orchestrateur :
    - ne lève PAS l'exception vers l'appelant,
    - persiste status=FAILED en DB,
    - renseigne last_error avec la stage incriminée et le message d'erreur.

NB: La fixture ``mock_external_services`` du conftest (autouse=True) est
active ici aussi — elle patche les méthodes au niveau de la classe. Les
``patch.object`` dans ces tests opèrent au niveau de l'instance et ont
priorité : ils surchargent sélectivement uniquement les méthodes testées.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models import detection, estimation, signalement as sig_model, user as user_model  # noqa: F401
from app.models.signalement import Signalement, SignalementStatus
from app.models.user import User, UserRole
from app.services.orchestrator import OrchestratorService
from app.core.testing_fakes import (
    FAKE_COST_ESTIMATION,
    FAKE_DETECTION_RESULT,
    FAKE_SCENARIOS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db(tmp_path) -> Session:
    """Base SQLite isolée par test, schéma complet créé au démarrage."""
    engine = create_engine(
        f"sqlite:///{tmp_path}/orchestrator_failure_test.db",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def pending_signalement(db: Session) -> Signalement:
    """Crée un utilisateur + signalement PENDING prêt à être traité."""
    owner = User(
        email="fail@example.com",
        username="fail_user",
        hashed_password="hashed_pw",
        full_name="Failure Test User",
        role=UserRole.CITIZEN,
        is_active=True,
    )
    db.add(owner)
    db.flush()

    sig = Signalement(
        title="Test échec pipeline",
        description="Ce signalement a pour vocation de provoquer une erreur.",
        image_path="/tmp/fake_image.jpg",
        latitude=34.7406,
        longitude=10.7603,
        city="Sfax",
        region="Sfax",
        user_id=owner.id,
        status=SignalementStatus.PENDING,
        progress=0,
    )
    db.add(sig)
    db.commit()
    db.refresh(sig)
    return sig


# ---------------------------------------------------------------------------
# Tests : cas d'erreur
# ---------------------------------------------------------------------------


class TestProcessSignalementDbFailure:
    """Vérifie la persistance FAILED + last_error quand une étape lève une exception."""

    def test_detection_failure_sets_status_failed(
        self, db: Session, pending_signalement: Signalement
    ) -> None:
        """Si detect_problems lève une exception, status doit valoir FAILED."""
        orchestrator = OrchestratorService()

        with patch.object(
            orchestrator.detection_svc,
            "detect_problems",
            side_effect=RuntimeError("YOLO model not available"),
        ):
            result = orchestrator.process_signalement_db(
                db=db,
                signalement_id=pending_signalement.id,
                generate_media=False,
                mock_services=False,
            )

        assert result["ok"] is False

        db.refresh(pending_signalement)
        assert pending_signalement.status == SignalementStatus.FAILED

    def test_failure_last_error_populated(
        self, db: Session, pending_signalement: Signalement
    ) -> None:
        """last_error doit contenir la stage et le message de l'exception."""
        orchestrator = OrchestratorService()
        error_message = "YOLO model not available"

        with patch.object(
            orchestrator.detection_svc,
            "detect_problems",
            side_effect=RuntimeError(error_message),
        ):
            orchestrator.process_signalement_db(
                db=db,
                signalement_id=pending_signalement.id,
                generate_media=False,
                mock_services=False,
            )

        db.refresh(pending_signalement)
        assert pending_signalement.last_error is not None
        assert pending_signalement.last_error.get("stage") == "detection"
        assert error_message in pending_signalement.last_error.get("message", "")

    def test_failure_stage_image_generation(
        self, db: Session, pending_signalement: Signalement
    ) -> None:
        """Échec à l'étape images : stage='images' capturée dans last_error."""
        orchestrator = OrchestratorService()

        with (
            patch.object(
                orchestrator.detection_svc,
                "detect_problems",
                return_value=FAKE_DETECTION_RESULT,
            ),
            patch.object(
                orchestrator.image_gen_svc,
                "generate_scenarios",
                side_effect=ConnectionError("Replicate API timeout"),
            ),
        ):
            orchestrator.process_signalement_db(
                db=db,
                signalement_id=pending_signalement.id,
                generate_media=False,
                mock_services=False,
            )

        db.refresh(pending_signalement)
        assert pending_signalement.last_error is not None
        assert pending_signalement.last_error.get("stage") == "images"
        assert "Replicate API timeout" in pending_signalement.last_error.get("message", "")

    def test_failure_stage_cost_estimation(
        self, db: Session, pending_signalement: Signalement
    ) -> None:
        """Échec à l'étape estimation de coût → status FAILED, stage='cost'."""
        orchestrator = OrchestratorService()

        with (
            patch.object(
                orchestrator.detection_svc,
                "detect_problems",
                return_value=FAKE_DETECTION_RESULT,
            ),
            patch.object(
                orchestrator.image_gen_svc,
                "generate_scenarios",
                return_value=list(FAKE_SCENARIOS),
            ),
            patch.object(
                orchestrator.cost_svc,
                "estimate_costs",
                side_effect=TimeoutError("Groq API timeout"),
            ),
        ):
            result = orchestrator.process_signalement_db(
                db=db,
                signalement_id=pending_signalement.id,
                generate_media=False,
                mock_services=False,
            )

        assert result["ok"] is False

        db.refresh(pending_signalement)
        assert pending_signalement.status == SignalementStatus.FAILED
        assert pending_signalement.last_error is not None
        assert pending_signalement.last_error.get("stage") == "cost"

    def test_failure_does_not_propagate_exception(
        self, db: Session, pending_signalement: Signalement
    ) -> None:
        """process_signalement_db ne doit jamais propager l'exception vers l'appelant."""
        orchestrator = OrchestratorService()

        with patch.object(
            orchestrator.detection_svc,
            "detect_problems",
            side_effect=MemoryError("Out of GPU memory"),
        ):
            # Doit retourner un dict, pas lever une exception
            result = orchestrator.process_signalement_db(
                db=db,
                signalement_id=pending_signalement.id,
                generate_media=False,
                mock_services=False,
            )

        assert result is not None
        assert isinstance(result, dict)
        assert result["ok"] is False

    def test_failure_progress_not_100(
        self, db: Session, pending_signalement: Signalement
    ) -> None:
        """Après un échec, progress ne doit pas atteindre 100."""
        orchestrator = OrchestratorService()

        with patch.object(
            orchestrator.detection_svc,
            "detect_problems",
            side_effect=RuntimeError("crash"),
        ):
            orchestrator.process_signalement_db(
                db=db,
                signalement_id=pending_signalement.id,
                generate_media=False,
                mock_services=False,
            )

        db.refresh(pending_signalement)
        assert pending_signalement.progress < 100

    def test_partial_success_then_audio_failure(
        self, db: Session, pending_signalement: Signalement
    ) -> None:
        """Échec durant la génération audio (avec generate_media=True) → FAILED."""
        orchestrator = OrchestratorService()

        with (
            patch.object(
                orchestrator.detection_svc,
                "detect_problems",
                return_value=FAKE_DETECTION_RESULT,
            ),
            patch.object(
                orchestrator.image_gen_svc,
                "generate_scenarios",
                return_value=list(FAKE_SCENARIOS),
            ),
            patch.object(
                orchestrator.cost_svc,
                "estimate_costs",
                return_value=FAKE_COST_ESTIMATION,
            ),
            patch.object(
                orchestrator.audio_svc,
                "generate_narration",
                side_effect=OSError("Bark model file missing"),
            ),
        ):
            result = orchestrator.process_signalement_db(
                db=db,
                signalement_id=pending_signalement.id,
                generate_media=True,
                mock_services=False,
            )

        assert result["ok"] is False

        db.refresh(pending_signalement)
        assert pending_signalement.status == SignalementStatus.FAILED
        assert pending_signalement.last_error is not None
        assert pending_signalement.last_error.get("stage") == "audio"
