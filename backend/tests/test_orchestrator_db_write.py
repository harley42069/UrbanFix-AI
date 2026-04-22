"""Tests d'intégration : process_signalement_db() + persistance DB (mode mock).

Ces tests vérifient que l'orchestrateur écrit correctement dans la base de
données après chaque étape du pipeline, sans aucun appel réseau ni GPU.
On utilise ``mock_services=True`` pour substituer tous les services IA par
les données déterministes de ``app.core.testing_fakes``.

Couverture :
    - status == COMPLETED après succès
    - progress == 100 en fin de pipeline
    - current_stage == "completed"
    - detections_data / scenarios_data / estimations_data non nuls
    - processing_time_seconds renseigné
    - completed_at renseigné
    - last_error == None après succès
    - retour ok=False si signalement introuvable
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models import detection, estimation, signalement as sig_model, user as user_model  # noqa: F401
from app.models.signalement import Signalement, SignalementStatus
from app.models.user import User, UserRole
from app.services.orchestrator import OrchestratorService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db(tmp_path) -> Session:
    """Base SQLite isolée par test, schéma complet créé au démarrage."""
    engine = create_engine(
        f"sqlite:///{tmp_path}/orchestrator_write_test.db",
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
    """Crée un utilisateur + signalement PENDING dans la DB de test."""
    owner = User(
        email="write@example.com",
        username="write_user",
        hashed_password="hashed_pw",
        full_name="Write Test User",
        role=UserRole.CITIZEN,
        is_active=True,
    )
    db.add(owner)
    db.flush()

    sig = Signalement(
        title="Nid de poule rue principale",
        description="Grande dégradation de la chaussée devant le marché.",
        image_path="/tmp/fake_image.jpg",  # inexistant – non accédé en mode mock
        latitude=36.8065,
        longitude=10.1815,
        city="Tunis",
        region="Tunis",
        user_id=owner.id,
        status=SignalementStatus.PENDING,
        progress=0,
    )
    db.add(sig)
    db.commit()
    db.refresh(sig)
    return sig


# ---------------------------------------------------------------------------
# Tests : succès pipeline (generate_media=False, mock_services=True)
# ---------------------------------------------------------------------------


class TestProcessSignalementDbWrite:
    """Vérifie l'écriture en DB par process_signalement_db() en mode mock."""

    def test_returns_ok_true(self, db: Session, pending_signalement: Signalement) -> None:
        """La valeur de retour doit indiquer ok=True et l'id correct."""
        orchestrator = OrchestratorService()
        result = orchestrator.process_signalement_db(
            db=db,
            signalement_id=pending_signalement.id,
            generate_media=False,
            mock_services=True,
        )

        assert result["ok"] is True
        assert result["signalement_id"] == pending_signalement.id

    def test_status_completed(self, db: Session, pending_signalement: Signalement) -> None:
        """Le statut final doit être COMPLETED."""
        orchestrator = OrchestratorService()
        orchestrator.process_signalement_db(
            db=db,
            signalement_id=pending_signalement.id,
            generate_media=False,
            mock_services=True,
        )

        db.refresh(pending_signalement)
        assert pending_signalement.status == SignalementStatus.COMPLETED

    def test_progress_100(self, db: Session, pending_signalement: Signalement) -> None:
        """La progression doit atteindre 100 en fin de pipeline."""
        orchestrator = OrchestratorService()
        orchestrator.process_signalement_db(
            db=db,
            signalement_id=pending_signalement.id,
            generate_media=False,
            mock_services=True,
        )

        db.refresh(pending_signalement)
        assert pending_signalement.progress == 100

    def test_current_stage_is_completed(
        self, db: Session, pending_signalement: Signalement
    ) -> None:
        """current_stage doit valoir 'completed' après succès."""
        orchestrator = OrchestratorService()
        orchestrator.process_signalement_db(
            db=db,
            signalement_id=pending_signalement.id,
            generate_media=False,
            mock_services=True,
        )

        db.refresh(pending_signalement)
        assert pending_signalement.current_stage == "completed"

    def test_detections_data_persisted(
        self, db: Session, pending_signalement: Signalement
    ) -> None:
        """detections_data doit être non nul et contenir 'total_problems'."""
        orchestrator = OrchestratorService()
        orchestrator.process_signalement_db(
            db=db,
            signalement_id=pending_signalement.id,
            generate_media=False,
            mock_services=True,
        )

        db.refresh(pending_signalement)
        assert pending_signalement.detections_data is not None
        assert "total_problems" in pending_signalement.detections_data
        assert pending_signalement.detections_data["total_problems"] >= 1

    def test_scenarios_data_persisted(
        self, db: Session, pending_signalement: Signalement
    ) -> None:
        """scenarios_data doit être non nul avec au moins 1 scénario."""
        orchestrator = OrchestratorService()
        orchestrator.process_signalement_db(
            db=db,
            signalement_id=pending_signalement.id,
            generate_media=False,
            mock_services=True,
        )

        db.refresh(pending_signalement)
        assert pending_signalement.scenarios_data is not None
        assert isinstance(pending_signalement.scenarios_data, list)
        assert len(pending_signalement.scenarios_data) == 3
        first = pending_signalement.scenarios_data[0]
        assert "scenario_type" in first
        assert "narration_text" in first

    def test_generate_media_sets_audio_pdf_urls_and_narration_text(
        self, db: Session, pending_signalement: Signalement
    ) -> None:
        """Avec generate_media=True, audio/pdf sont remplis et chaque scenario a narration_text."""
        orchestrator = OrchestratorService()
        orchestrator.process_signalement_db(
            db=db,
            signalement_id=pending_signalement.id,
            generate_media=True,
            mock_services=True,
        )

        db.refresh(pending_signalement)
        assert pending_signalement.audio_url is not None
        assert pending_signalement.pdf_url is not None
        assert isinstance(pending_signalement.scenarios_data, list)
        assert len(pending_signalement.scenarios_data) == 3
        assert all(s.get("narration_text") for s in pending_signalement.scenarios_data)

    def test_estimations_data_persisted(
        self, db: Session, pending_signalement: Signalement
    ) -> None:
        """estimations_data doit être non nul et contenir 'total_cost_tnd'."""
        orchestrator = OrchestratorService()
        orchestrator.process_signalement_db(
            db=db,
            signalement_id=pending_signalement.id,
            generate_media=False,
            mock_services=True,
        )

        db.refresh(pending_signalement)
        assert pending_signalement.estimations_data is not None
        assert "total_cost_tnd" in pending_signalement.estimations_data
        assert pending_signalement.estimations_data["total_cost_tnd"] > 0

    def test_processing_time_set(
        self, db: Session, pending_signalement: Signalement
    ) -> None:
        """processing_time_seconds doit être renseigné et >= 0."""
        orchestrator = OrchestratorService()
        orchestrator.process_signalement_db(
            db=db,
            signalement_id=pending_signalement.id,
            generate_media=False,
            mock_services=True,
        )

        db.refresh(pending_signalement)
        assert pending_signalement.processing_time_seconds is not None
        assert pending_signalement.processing_time_seconds >= 0.0

    def test_completed_at_set(
        self, db: Session, pending_signalement: Signalement
    ) -> None:
        """completed_at doit être renseigné après succès."""
        orchestrator = OrchestratorService()
        orchestrator.process_signalement_db(
            db=db,
            signalement_id=pending_signalement.id,
            generate_media=False,
            mock_services=True,
        )

        db.refresh(pending_signalement)
        assert pending_signalement.completed_at is not None

    def test_no_last_error_on_success(
        self, db: Session, pending_signalement: Signalement
    ) -> None:
        """last_error doit être None après un pipeline réussi."""
        orchestrator = OrchestratorService()
        orchestrator.process_signalement_db(
            db=db,
            signalement_id=pending_signalement.id,
            generate_media=False,
            mock_services=True,
        )

        db.refresh(pending_signalement)
        assert pending_signalement.last_error is None

    def test_not_found_returns_error(self, db: Session) -> None:
        """ok=False si le signalement demandé n'existe pas en DB."""
        orchestrator = OrchestratorService()
        result = orchestrator.process_signalement_db(
            db=db,
            signalement_id=99999,
            generate_media=False,
            mock_services=True,
        )

        assert result["ok"] is False
        assert result["error"] == "signalement_not_found"

    def test_idempotent_call_does_not_raise(
        self, db: Session, pending_signalement: Signalement
    ) -> None:
        """Appeler process_signalement_db deux fois de suite ne doit pas lever d'exception."""
        orchestrator = OrchestratorService()
        orchestrator.process_signalement_db(
            db=db,
            signalement_id=pending_signalement.id,
            generate_media=False,
            mock_services=True,
        )
        result = orchestrator.process_signalement_db(
            db=db,
            signalement_id=pending_signalement.id,
            generate_media=False,
            mock_services=True,
        )

        # Le second appel doit retourner un dict valide (ok=True ou ok=False)
        assert isinstance(result, dict)
        assert "ok" in result
