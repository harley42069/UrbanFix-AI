"""Seed minimal: 1 admin, 1 user, 1 signalement."""

from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.models.signalement import Signalement, SignalementStatus
from app.core.security import get_password_hash


def run_seed() -> None:
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@urbanfix.tn", User.is_deleted.is_(False)).first()
        if not admin:
            admin = User(
                email="admin@urbanfix.tn",
                username="admin",
                hashed_password=get_password_hash("Admin123!"),
                full_name="UrbanFix Admin",
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True,
            )
            db.add(admin)

        user = db.query(User).filter(User.email == "user@urbanfix.tn", User.is_deleted.is_(False)).first()
        if not user:
            user = User(
                email="user@urbanfix.tn",
                username="citizen01",
                hashed_password=get_password_hash("User12345!"),
                full_name="Citizen One",
                role=UserRole.CITIZEN,
                is_active=True,
                is_verified=True,
            )
            db.add(user)

        db.flush()

        existing_signalement = (
            db.query(Signalement)
            .filter(
                Signalement.user_id == user.id,
                Signalement.title == "Chaussée dégradée Avenue Habib Bourguiba",
                Signalement.is_deleted.is_(False),
            )
            .first()
        )

        if not existing_signalement:
            signalement = Signalement(
                title="Chaussée dégradée Avenue Habib Bourguiba",
                description="Nids-de-poule multiples et marquage effacé",
                image_path="uploads/sample_road.jpg",
                image_url=None,
                latitude=36.8065,
                longitude=10.1815,
                address="Avenue Habib Bourguiba",
                city="Tunis",
                region="Tunis",
                status=SignalementStatus.PENDING,
                user_id=user.id,
                metadata_json={"source": "seed", "note": "sample data"},
                schema_version=1,
            )
            db.add(signalement)

        db.commit()
        print("Seed minimal appliqué avec succès.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
