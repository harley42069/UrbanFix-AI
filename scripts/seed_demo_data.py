"""Seed deterministic demo data for UrbanFix AI soutenance.

Usage:
    python scripts/seed_demo_data.py
    python scripts/seed_demo_data.py --run-process

This script:
1) creates (or reuses) a demo user,
2) inserts two demo signalements,
3) optionally runs process on one signalement (generate_media=False, mock_services=True).
"""

from __future__ import annotations

import argparse
import base64
import os
import sys
from pathlib import Path
from typing import Iterable

# Ensure backend package imports work when script is called from repo root.
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Keep relative DATABASE_URL (sqlite:///./urbanfix.db) anchored to backend dir.
os.chdir(BACKEND_ROOT)

from app.db.session import SessionLocal, init_db
from app.models.signalement import Signalement, SignalementStatus
from app.models.user import User, UserRole
from app.services.orchestrator import OrchestratorService

DEMO_EMAIL = "demo@urbanfix.local"
DEMO_USERNAME = "urbanfix_demo"
DEMO_PASSWORD = "Demo12345!"
DEMO_HASH = "demo_hash_not_for_prod"


def log(message: str) -> None:
    print(f"[seed_demo_data] {message}")


def ensure_placeholder_image(path: Path) -> None:
    """Write a minimal 1x1 PNG if image does not exist."""
    if path.exists():
        return

    png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
        "/w8AAn8B9pV4igAAAABJRU5ErkJggg=="
    )
    data = base64.b64decode(png_b64)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def pick_demo_images() -> list[Path]:
    """Return two local images for demo, creating placeholders if needed."""
    candidates: Iterable[Path] = [
        BACKEND_ROOT / "temp" / "swagger_e2e.jpg",
        BACKEND_ROOT / "temp" / "e2e_swagger.jpg",
    ]

    picked = [p for p in candidates if p.exists()]
    if len(picked) >= 2:
        return picked[:2]

    fallback_dir = BACKEND_ROOT / "temp" / "demo_seed"
    img1 = fallback_dir / "demo_1.png"
    img2 = fallback_dir / "demo_2.png"
    ensure_placeholder_image(img1)
    ensure_placeholder_image(img2)
    return [img1, img2]


def ensure_demo_user(db) -> User:
    user = db.query(User).filter(User.email == DEMO_EMAIL).first()
    if user:
        log(f"Demo user already exists: {user.email} (id={user.id})")
        return user

    user = User(
        email=DEMO_EMAIL,
        username=DEMO_USERNAME,
        hashed_password=DEMO_HASH,
        full_name="UrbanFix Demo User",
        role=UserRole.CITIZEN,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log(f"Created demo user: {user.email} (id={user.id})")
    return user


def create_demo_signalements(db, user: User, images: list[Path]) -> list[Signalement]:
    payloads = [
        {
            "title": "Nid de poule - Avenue Habib Bourguiba",
            "description": "Chaussée très dégradée, circulation difficile.",
            "latitude": 36.8065,
            "longitude": 10.1815,
            "city": "Tunis",
            "region": "Tunis",
            "address": "Avenue Habib Bourguiba",
            "image_path": str(images[0]),
        },
        {
            "title": "Eclairage public défectueux - Sfax centre",
            "description": "Plusieurs lampadaires ne fonctionnent plus la nuit.",
            "latitude": 34.7406,
            "longitude": 10.7603,
            "city": "Sfax",
            "region": "Sfax",
            "address": "Centre-ville Sfax",
            "image_path": str(images[1]),
        },
    ]

    created: list[Signalement] = []
    for item in payloads:
        existing = (
            db.query(Signalement)
            .filter(
                Signalement.user_id == user.id,
                Signalement.title == item["title"],
                Signalement.is_deleted.is_(False),
            )
            .first()
        )
        if existing:
            log(f"Signalement already exists: {existing.title} (id={existing.id})")
            created.append(existing)
            continue

        sig = Signalement(
            title=item["title"],
            description=item["description"],
            image_path=item["image_path"],
            latitude=item["latitude"],
            longitude=item["longitude"],
            address=item["address"],
            city=item["city"],
            region=item["region"],
            user_id=user.id,
            status=SignalementStatus.PENDING,
            progress=0,
            current_stage="queued",
        )
        db.add(sig)
        db.commit()
        db.refresh(sig)
        created.append(sig)
        log(f"Created signalement: {sig.title} (id={sig.id})")

    return created


def optionally_process_one(db, signalements: list[Signalement]) -> None:
    if not signalements:
        log("No signalements to process.")
        return

    target = signalements[0]
    log(
        "Triggering process on signalement "
        f"id={target.id} (generate_media=False, mock_services=True)..."
    )
    orchestrator = OrchestratorService()
    result = orchestrator.process_signalement_db(
        db=db,
        signalement_id=target.id,
        generate_media=False,
        mock_services=True,
    )
    log(f"Process result: {result}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed UrbanFix AI demo data.")
    parser.add_argument(
        "--run-process",
        action="store_true",
        help="Run pipeline once on first seeded signalement (mock/offline).",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        init_db()
        images = pick_demo_images()
        log(f"Using images: {[str(p) for p in images]}")

        user = ensure_demo_user(db)
        signalements = create_demo_signalements(db, user, images)

        if args.run_process:
            optionally_process_one(db, signalements)

        log("Done.")
        log(f"Demo credentials -> email: {DEMO_EMAIL} | password: {DEMO_PASSWORD}")
        return 0
    except Exception as exc:
        log(f"ERROR: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
